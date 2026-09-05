import { Prisma, PersonalRecordType, SetType, WorkoutStatus, type PrismaClient } from '@prisma/client';
import { HttpError } from '../../lib/http-error.js';
import { estimateOneRepMax, toDecimal } from '../../lib/decimal.js';
import { prisma } from '../../lib/prisma.js';
import { serializeWorkout, type SerializedWorkout } from './workout.mapper.js';
import type { CreateWorkoutInput, ListWorkoutsQuery, SetInput } from './workout.schema.js';

type Tx = Prisma.TransactionClient | PrismaClient;

const fullWorkoutInclude = {
  exercises: {
    orderBy: { position: 'asc' },
    include: {
      exercise: true,
      sets: { orderBy: { setNumber: 'asc' } },
    },
  },
} satisfies Prisma.WorkoutInclude;

/** Warm-ups are practice, not work: they never count toward volume or PRs. */
const countsAsWorkingSet = (set: SetInput): boolean =>
  set.isCompleted && set.setType !== SetType.WARMUP;

interface Totals {
  volumeKg: number;
  sets: number;
  reps: number;
}

function computeTotals(input: CreateWorkoutInput): Totals {
  let volumeKg = 0;
  let sets = 0;
  let reps = 0;

  for (const exercise of input.exercises) {
    for (const set of exercise.sets) {
      if (!countsAsWorkingSet(set)) continue;
      sets += 1;
      reps += set.reps ?? 0;
      volumeKg += (set.weightKg ?? 0) * (set.reps ?? 0);
    }
  }

  return { volumeKg: Number(volumeKg.toFixed(2)), sets, reps };
}

/** A single candidate record produced by one completed set. */
interface RecordCandidate {
  type: PersonalRecordType;
  value: number;
  weightKg: number | null;
  reps: number | null;
  workoutSetId: string;
}

function candidatesFor(set: SetInput, workoutSetId: string): RecordCandidate[] {
  const weightKg = set.weightKg ?? null;
  const reps = set.reps ?? null;
  const candidates: RecordCandidate[] = [];

  if (weightKg != null && weightKg > 0) {
    candidates.push({ type: PersonalRecordType.MAX_WEIGHT, value: weightKg, weightKg, reps, workoutSetId });
  }
  if (reps != null && reps > 0) {
    candidates.push({ type: PersonalRecordType.MAX_REPS, value: reps, weightKg, reps, workoutSetId });
  }
  if (weightKg != null && reps != null && weightKg > 0 && reps > 0) {
    candidates.push({
      type: PersonalRecordType.BEST_SET_VOLUME,
      value: Number((weightKg * reps).toFixed(2)),
      weightKg,
      reps,
      workoutSetId,
    });
    const oneRm = estimateOneRepMax(weightKg, reps);
    if (oneRm != null) {
      candidates.push({ type: PersonalRecordType.ESTIMATED_1RM, value: oneRm, weightKg, reps, workoutSetId });
    }
  }

  return candidates;
}

export interface PersonalRecordHit {
  exerciseId: string;
  exerciseName: string;
  type: PersonalRecordType;
  value: number;
  previousValue: number | null;
}

/**
 * Compare every completed set against the user's current bests and upgrade the
 * `PersonalRecord` rows that improved. Runs inside the create transaction so a
 * failed workout write never leaves a phantom PR behind.
 */
async function updatePersonalRecords(
  tx: Tx,
  userId: string,
  perExercise: { exerciseId: string; exerciseName: string; candidates: RecordCandidate[] }[],
): Promise<PersonalRecordHit[]> {
  const hits: PersonalRecordHit[] = [];

  for (const { exerciseId, exerciseName, candidates } of perExercise) {
    if (candidates.length === 0) continue;

    // Keep only the best candidate per record type for this workout.
    const best = new Map<PersonalRecordType, RecordCandidate>();
    for (const candidate of candidates) {
      const current = best.get(candidate.type);
      if (!current || candidate.value > current.value) best.set(candidate.type, candidate);
    }

    const existing = await tx.personalRecord.findMany({ where: { userId, exerciseId } });
    const existingByType = new Map(existing.map((record) => [record.type, record]));

    for (const [type, candidate] of best) {
      const current = existingByType.get(type);
      const previousValue = current ? current.value.toNumber() : null;
      if (previousValue != null && previousValue >= candidate.value) continue;

      await tx.personalRecord.upsert({
        where: { userId_exerciseId_type: { userId, exerciseId, type } },
        create: {
          userId,
          exerciseId,
          type,
          value: new Prisma.Decimal(candidate.value),
          weightKg: toDecimal(candidate.weightKg),
          reps: candidate.reps,
          workoutSetId: candidate.workoutSetId,
        },
        update: {
          value: new Prisma.Decimal(candidate.value),
          weightKg: toDecimal(candidate.weightKg),
          reps: candidate.reps,
          workoutSetId: candidate.workoutSetId,
          achievedAt: new Date(),
        },
      });

      hits.push({ exerciseId, exerciseName, type, value: candidate.value, previousValue });
    }
  }

  return hits;
}

export interface CreateWorkoutResult {
  workout: SerializedWorkout;
  personalRecords: PersonalRecordHit[];
}

/**
 * Persist a finished workout together with its exercises and sets, then refresh
 * the user's personal records. The whole thing is one transaction.
 */
export async function createWorkout(
  userId: string,
  input: CreateWorkoutInput,
): Promise<CreateWorkoutResult> {
  const exerciseIds = [...new Set(input.exercises.map((item) => item.exerciseId))];

  // Reject unknown ids up front so we fail with a useful message rather than a
  // foreign-key violation. Custom exercises are visible only to their owner.
  const exercises = await prisma.exercise.findMany({
    where: { id: { in: exerciseIds }, OR: [{ createdById: null }, { createdById: userId }] },
    select: { id: true, name: true },
  });

  if (exercises.length !== exerciseIds.length) {
    const found = new Set(exercises.map((exercise) => exercise.id));
    const missing = exerciseIds.filter((id) => !found.has(id));
    throw HttpError.badRequest('Unknown exercise id(s)', { missing });
  }

  const nameById = new Map(exercises.map((exercise) => [exercise.id, exercise.name]));
  const totals = computeTotals(input);
  const finishedAt =
    input.finishedAt ?? (input.status === WorkoutStatus.COMPLETED ? new Date() : null);
  const durationSec =
    input.durationSec ??
    (finishedAt ? Math.max(0, Math.round((finishedAt.getTime() - input.startedAt.getTime()) / 1000)) : null);

  return prisma.$transaction(async (tx) => {
    const workout = await tx.workout.create({
      data: {
        userId,
        title: input.title,
        notes: input.notes ?? null,
        status: input.status,
        startedAt: input.startedAt,
        finishedAt,
        durationSec,
        totalVolumeKg: new Prisma.Decimal(totals.volumeKg),
        totalSets: totals.sets,
        totalReps: totals.reps,
        exercises: {
          create: input.exercises.map((exercise, position) => ({
            exerciseId: exercise.exerciseId,
            position,
            notes: exercise.notes ?? null,
            restSeconds: exercise.restSeconds ?? null,
            sets: {
              create: exercise.sets.map((set, index) => ({
                setNumber: index + 1,
                setType: set.setType,
                weightKg: toDecimal(set.weightKg),
                reps: set.reps ?? null,
                rpe: toDecimal(set.rpe),
                durationSec: set.durationSec ?? null,
                distanceM: toDecimal(set.distanceM),
                isCompleted: set.isCompleted,
                completedAt: set.isCompleted ? (set.completedAt ?? new Date()) : null,
              })),
            },
          })),
        },
      },
      include: fullWorkoutInclude,
    });

    // Only completed, non-warmup sets are eligible for a PR.
    const perExercise = workout.exercises.map((workoutExercise) => {
      const source = input.exercises[workoutExercise.position];
      const candidates: RecordCandidate[] = [];

      workoutExercise.sets.forEach((persistedSet, index) => {
        const set = source?.sets[index];
        if (!set || !countsAsWorkingSet(set)) return;
        candidates.push(...candidatesFor(set, persistedSet.id));
      });

      return {
        exerciseId: workoutExercise.exerciseId,
        exerciseName: nameById.get(workoutExercise.exerciseId) ?? workoutExercise.exercise.name,
        candidates,
      };
    });

    const personalRecords =
      input.status === WorkoutStatus.COMPLETED
        ? await updatePersonalRecords(tx, userId, perExercise)
        : [];

    return { workout: serializeWorkout(workout), personalRecords };
  });
}

export async function listWorkouts(
  userId: string,
  query: ListWorkoutsQuery,
): Promise<{ items: SerializedWorkout[]; nextCursor: string | null }> {
  const workouts = await prisma.workout.findMany({
    where: { userId, ...(query.status ? { status: query.status } : {}) },
    orderBy: { startedAt: 'desc' },
    take: query.limit + 1,
    ...(query.cursor ? { cursor: { id: query.cursor }, skip: 1 } : {}),
    include: fullWorkoutInclude,
  });

  const hasMore = workouts.length > query.limit;
  const page = hasMore ? workouts.slice(0, query.limit) : workouts;

  return {
    items: page.map(serializeWorkout),
    nextCursor: hasMore ? (page.at(-1)?.id ?? null) : null,
  };
}

export async function getWorkout(userId: string, workoutId: string): Promise<SerializedWorkout> {
  const workout = await prisma.workout.findFirst({
    where: { id: workoutId, userId },
    include: fullWorkoutInclude,
  });

  if (!workout) throw HttpError.notFound('Workout not found');
  return serializeWorkout(workout);
}

export async function deleteWorkout(userId: string, workoutId: string): Promise<void> {
  const { count } = await prisma.workout.deleteMany({ where: { id: workoutId, userId } });
  if (count === 0) throw HttpError.notFound('Workout not found');
}
