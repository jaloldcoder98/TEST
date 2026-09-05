/**
 * Unit tests for Telegram initData verification: real HMAC signatures,
 * tampering, wrong token, staleness, and the Ed25519 `signature` field.
 *   npm run test:unit
 */
import { createHmac } from 'node:crypto';
import { verifyTelegramInitData, InitDataError } from '../src/lib/telegram-init-data.js';

const BOT_TOKEN = '7654321:AAH-fake-token-for-tests';

function sign(fields: Record<string, string>): string {
  const params = new URLSearchParams(fields);
  const dcs = [...params.entries()].map(([k, v]) => `${k}=${v}`).sort().join('\n');
  const secret = createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
  params.set('hash', createHmac('sha256', secret).update(dcs).digest('hex'));
  return params.toString();
}

const now = Math.floor(Date.now() / 1000);
const user = JSON.stringify({ id: 6543210987, first_name: 'Jaloliddin', username: 'jalol', is_premium: true });

let pass = 0, fail = 0;
const check = (name: string, fn: () => void) => {
  try { fn(); console.log(`  PASS  ${name}`); pass++; }
  catch (e) { console.log(`  FAIL  ${name}: ${(e as Error).message}`); fail++; }
};

check('valid initData is accepted', () => {
  const parsed = verifyTelegramInitData(sign({ user, auth_date: String(now), query_id: 'AA1' }), BOT_TOKEN, 86400);
  if (parsed.user.id !== 6543210987n) throw new Error(`bad id ${parsed.user.id}`);
  if (parsed.user.username !== 'jalol') throw new Error('bad username');
  if (parsed.user.is_premium !== true) throw new Error('bad is_premium');
  if (parsed.queryId !== 'AA1') throw new Error('bad query_id');
});

check('tampered field is rejected', () => {
  const signed = sign({ user, auth_date: String(now) });
  const forged = signed.replace('6543210987', '1111111111');
  try { verifyTelegramInitData(forged, BOT_TOKEN, 86400); } 
  catch (e) { if ((e as InitDataError).reason === 'BAD_SIGNATURE') return; throw e; }
  throw new Error('forged payload was accepted');
});

check('wrong bot token is rejected', () => {
  try { verifyTelegramInitData(sign({ user, auth_date: String(now) }), 'other:token', 86400); }
  catch (e) { if ((e as InitDataError).reason === 'BAD_SIGNATURE') return; throw e; }
  throw new Error('wrong-token payload was accepted');
});

check('stale initData is rejected', () => {
  try { verifyTelegramInitData(sign({ user, auth_date: String(now - 90000) }), BOT_TOKEN, 86400); }
  catch (e) { if ((e as InitDataError).reason === 'EXPIRED') return; throw e; }
  throw new Error('stale payload was accepted');
});

check('missing hash is rejected', () => {
  try { verifyTelegramInitData(`user=${encodeURIComponent(user)}&auth_date=${now}`, BOT_TOKEN, 86400); }
  catch (e) { if ((e as InitDataError).reason === 'MISSING_HASH') return; throw e; }
  throw new Error('unsigned payload was accepted');
});

check('signature field is excluded from the check string', () => {
  // Telegram's newer third-party scheme adds `signature`; it must not break HMAC validation.
  const params = new URLSearchParams(sign({ user, auth_date: String(now) }));
  params.set('signature', 'ed25519-blob');
  verifyTelegramInitData(params.toString(), BOT_TOKEN, 86400);
});

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
