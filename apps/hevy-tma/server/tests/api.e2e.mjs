/**
 * End-to-end API checks: signature auth, workout persistence, PR detection,
 * validation, per-user isolation, and stats. Plain Node, no test framework.
 */
import { createHmac } from 'node:crypto';

// Point these at a server running against a THROWAWAY database — the suite
// writes workouts and personal records.
//   E2E_BASE_URL=http://localhost:4000 E2E_BOT_TOKEN=<token> npm run test:e2e
const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:4111';
const BOT_TOKEN = process.env.E2E_BOT_TOKEN ?? '7654321:AAH-fake-token-for-tests';

// Fresh Telegram ids per run so the suite is idempotent: every assertion is
// scoped to a user nobody has written data for yet.
const PRIMARY_ID = 900_000_000_000 + Math.floor(Math.random() * 1_000_000);
const OTHER_ID = PRIMARY_ID + 1;

function initData(userId = PRIMARY_ID) {
  const p = new URLSearchParams({
    user: JSON.stringify({ id: userId, first_name: 'Jaloliddin', username: 'jalol' }),
    auth_date: String(Math.floor(Date.now() / 1000)),
  });
  const dcs = [...p.entries()].map(([k, v]) => `${k}=${v}`).sort().join('\n');
  const secret = createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
  p.set('hash', createHmac('sha256', secret).update(dcs).digest('hex'));
  return p.toString();
}

async function call(path, opts = {}, id = initData()) {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', 'X-Telegram-Init-Data': id, ...opts.headers },
  });
  const text = await res.text();
  return { status: res.status, body: text ? JSON.parse(text) : null };
}

let fails = 0;
const assert = (cond, msg, extra) => {
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${msg}`);
  if (!cond) { fails++; if (extra !== undefined) console.log('        ', JSON.stringify(extra).slice(0, 400)); }
};

// --- auth ---
const noAuth = await fetch(`${BASE}/api/me`).then((r) => r.status);
assert(noAuth === 401, 'unauthenticated request is rejected (401)', noAuth);

const forged = await call('/api/me', {}, initData().replace(/hash=.*/, 'hash=' + 'a'.repeat(64)));
assert(forged.status === 401, 'forged signature is rejected (401)', forged.body);

const me = await call('/api/me');
assert(me.status === 200 && me.body.user.telegramId === String(PRIMARY_ID), 'signed request authenticates + upserts user', me.body);

// --- exercises ---
const bench = await call('/api/exercises?q=bench%20press&limit=5');
assert(bench.status === 200 && bench.body.items.length > 0, 'exercise search returns results', bench.body?.error);
const chest = await call('/api/exercises?muscleGroup=CHEST&limit=3');
assert(chest.body.items.every((e) => e.muscleGroup === 'CHEST'), 'muscleGroup filter works');
const groups = await call('/api/exercises/muscle-groups');
assert(groups.body.items.length > 10, `muscle-group counts returned (${groups.body.items.length} groups)`);

const ex1 = bench.body.items[0].id;
const ex2 = chest.body.items[0].id;

// --- workout 1 ---
const started = new Date(Date.now() - 45 * 60 * 1000).toISOString();
const w1 = await call('/api/workouts', {
  method: 'POST',
  body: JSON.stringify({
    title: 'Push Day', status: 'COMPLETED', startedAt: started, finishedAt: new Date().toISOString(),
    exercises: [
      { exerciseId: ex1, restSeconds: 120, sets: [
        { setType: 'WARMUP', weightKg: 40, reps: 10, isCompleted: true },
        { setType: 'NORMAL', weightKg: 80, reps: 8, rpe: 7.5, isCompleted: true },
        { setType: 'NORMAL', weightKg: 90, reps: 5, rpe: 9, isCompleted: true },
        { setType: 'FAILURE', weightKg: 70, reps: 12, rpe: 10, isCompleted: true },
      ] },
      { exerciseId: ex2, sets: [{ setType: 'NORMAL', weightKg: 30, reps: 12, isCompleted: true }] },
    ],
  }),
});
assert(w1.status === 201, 'POST /api/workouts creates a workout (201)', w1.body);

// Volume excludes the warm-up: 80*8 + 90*5 + 70*12 + 30*12 = 640+450+840+360 = 2290
assert(w1.body.workout.totalVolumeKg === 2290, `volume excludes warm-ups (got ${w1.body.workout.totalVolumeKg}, want 2290)`);
assert(w1.body.workout.totalSets === 4, `set count excludes warm-ups (got ${w1.body.workout.totalSets}, want 4)`);
assert(w1.body.workout.durationSec >= 2700, `duration derived from timestamps (${w1.body.workout.durationSec}s)`);
assert(w1.body.workout.exercises[0].sets[1].rpe === 7.5, 'RPE round-trips as a number, not a string');
assert(w1.body.workout.exercises[0].sets[0].setType === 'WARMUP', 'set_type persists');

const prs = w1.body.personalRecords;
const maxWeight = prs.find((p) => p.type === 'MAX_WEIGHT');
assert(maxWeight?.value === 90, `MAX_WEIGHT PR = 90 (got ${maxWeight?.value})`);
const maxReps = prs.find((p) => p.type === 'MAX_REPS');
assert(maxReps?.value === 12, `MAX_REPS PR = 12, warm-up's 10 not counted (got ${maxReps?.value})`);
const oneRm = prs.find((p) => p.type === 'ESTIMATED_1RM');
assert(oneRm?.value === 105, `ESTIMATED_1RM = 90*(1+5/30) = 105 (got ${oneRm?.value})`);
assert(prs.every((p) => p.previousValue === null), 'first workout reports no previous values');

// --- workout 2: beat one PR, not the others ---
const w2 = await call('/api/workouts', {
  method: 'POST',
  body: JSON.stringify({
    title: 'Push Day 2', status: 'COMPLETED', startedAt: new Date().toISOString(),
    exercises: [{ exerciseId: ex1, sets: [{ setType: 'NORMAL', weightKg: 95, reps: 3, isCompleted: true }] }],
  }),
});
const p2 = w2.body.personalRecords;
assert(p2.some((p) => p.type === 'MAX_WEIGHT' && p.value === 95 && p.previousValue === 90),
  'improved MAX_WEIGHT is recorded with its previous value', p2);
assert(!p2.some((p) => p.type === 'MAX_REPS'), 'unbeaten MAX_REPS is not re-reported');
assert(!p2.some((p) => p.type === 'ESTIMATED_1RM'), '95x3 (=104.5) does not beat the 105 1RM');

// --- validation ---
const badRpe = await call('/api/workouts', { method: 'POST', body: JSON.stringify({
  status: 'COMPLETED', startedAt: new Date().toISOString(),
  exercises: [{ exerciseId: ex1, sets: [{ weightKg: 50, reps: 5, rpe: 11 }] }] }) });
assert(badRpe.status === 400, 'RPE above 10 is rejected (400)', badRpe.body);

const oddRpe = await call('/api/workouts', { method: 'POST', body: JSON.stringify({
  status: 'COMPLETED', startedAt: new Date().toISOString(),
  exercises: [{ exerciseId: ex1, sets: [{ weightKg: 50, reps: 5, rpe: 7.3 }] }] }) });
assert(oddRpe.status === 400, 'RPE off the 0.5 grid is rejected (400)');

const noSets = await call('/api/workouts', { method: 'POST', body: JSON.stringify({
  status: 'COMPLETED', startedAt: new Date().toISOString(), exercises: [{ exerciseId: ex1, sets: [] }] }) });
assert(noSets.status === 400, 'exercise with zero sets is rejected (400)');

const badId = await call('/api/workouts', { method: 'POST', body: JSON.stringify({
  status: 'COMPLETED', startedAt: new Date().toISOString(),
  exercises: [{ exerciseId: '00000000-0000-4000-8000-000000000000', sets: [{ weightKg: 50, reps: 5 }] }] }) });
assert(badId.status === 400 && badId.body.error.details?.missing?.length === 1,
  'unknown exercise id fails with a useful message', badId.body);

// --- isolation between users ---
const other = initData(OTHER_ID);
const otherList = await call('/api/workouts', {}, other);
assert(otherList.body.items.length === 0, "another user cannot see this user's workouts");
const steal = await call(`/api/workouts/${w1.body.workout.id}`, {}, other);
assert(steal.status === 404, "another user cannot read this user's workout by id", steal.body);

// --- stats ---
const summary = await call('/api/stats/summary');
assert(summary.body.totals.workouts === 2, `2 workouts counted (got ${summary.body.totals.workouts})`);
assert(summary.body.totals.volumeKg === 2575, `total volume 2290+285 = 2575 (got ${summary.body.totals.volumeKg})`);
assert(summary.body.weeklyVolume.length === 12, `12 weekly buckets, gaps filled (got ${summary.body.weeklyVolume.length})`);
assert(summary.body.weeklyVolume.at(-1).workouts === 2, 'this week holds both workouts');

const prList = await call('/api/stats/personal-records');
assert(prList.body.items.length === 8, `8 PR rows: 4 types x 2 exercises (got ${prList.body.items.length})`);
assert(prList.body.items.every((p) => typeof p.value === 'number'), 'PR values serialize as numbers');

// --- history + delete ---
const list = await call('/api/workouts?limit=10');
assert(list.body.items.length === 2 && list.body.items[0].title === 'Push Day 2', 'history is newest-first');
const del = await call(`/api/workouts/${w2.body.workout.id}`, { method: 'DELETE' });
assert(del.status === 204, 'DELETE returns 204');
const afterDel = await call('/api/workouts?limit=10');
assert(afterDel.body.items.length === 1, 'deleted workout is gone');

// --- custom exercise ---
const custom = await call('/api/exercises', { method: 'POST', body: JSON.stringify({
  name: `Uzbek Get-Up ${PRIMARY_ID}`, muscleGroup: 'FULL_BODY', equipment: 'KETTLEBELL' }) });
assert(custom.status === 201, 'custom exercise created (201)', custom.body);
const mine = await call(`/api/exercises?q=${encodeURIComponent(`Uzbek Get-Up ${PRIMARY_ID}`)}`);
assert(mine.body.items.length === 1 && mine.body.items[0].isCustom === true, 'owner sees their custom exercise');
const theirs = await call(`/api/exercises?q=${encodeURIComponent(`Uzbek Get-Up ${PRIMARY_ID}`)}`, {}, other);
assert(theirs.body.items.length === 0, "another user does not see someone else's custom exercise");

console.log(fails === 0 ? '\nAll checks passed.' : `\n${fails} check(s) FAILED.`);
process.exit(fails === 0 ? 0 : 1);
