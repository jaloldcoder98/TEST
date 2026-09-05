/**
 * Seeds the exercise library from the repository's exercise dataset
 * (`data/exercises/exercises.en.json`, 1323 entries with GIF/thumbnail URLs).
 *
 * Idempotent: re-running upserts by slug, so it is safe in CI and on deploy.
 *
 *   npm run seed
 *   EXERCISES_DATASET=/path/to/exercises.en.json npm run seed
 */
import { readFile } from 'node:fs/promises';
import { dirname, isAbsolute, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Equipment, ExerciseKind, MuscleGroup, PrismaClient } from '@prisma/client';

const here = dirname(fileURLToPath(import.meta.url));
const DEFAULT_DATASET = resolve(here, '../../../../data/exercises/exercises.en.json');

interface DatasetExercise {
  slug: string;
  name: string;
  muscle: string;
  bodyPart: string;
  equipment: string;
  category: string;
  secondaryMuscles?: string[];
  instructions?: string[];
  gifUrl?: string;
  thumbUrl?: string;
}

const MUSCLE_MAP: Record<string, MuscleGroup> = {
  abductors: MuscleGroup.ABDUCTORS,
  abs: MuscleGroup.ABS,
  adductors: MuscleGroup.ADDUCTORS,
  biceps: MuscleGroup.BICEPS,
  calves: MuscleGroup.CALVES,
  cardio: MuscleGroup.CARDIO,
  delts: MuscleGroup.SHOULDERS,
  forearms: MuscleGroup.FOREARMS,
  glutes: MuscleGroup.GLUTES,
  hamstrings: MuscleGroup.HAMSTRINGS,
  lats: MuscleGroup.BACK,
  'levator-scapulae': MuscleGroup.NECK,
  pectorals: MuscleGroup.CHEST,
  quads: MuscleGroup.QUADS,
  'serratus-anterior': MuscleGroup.CHEST,
  spine: MuscleGroup.BACK,
  traps: MuscleGroup.TRAPS,
  triceps: MuscleGroup.TRICEPS,
  'upper-back': MuscleGroup.BACK,
};

const EQUIPMENT_MAP: Record<string, Equipment> = {
  band: Equipment.BAND,
  barbell: Equipment.BARBELL,
  bodyweight: Equipment.BODYWEIGHT,
  cable: Equipment.CABLE,
  dumbbell: Equipment.DUMBBELL,
  'ez-bar': Equipment.BARBELL,
  kettlebell: Equipment.KETTLEBELL,
  lever: Equipment.MACHINE,
  machine: Equipment.MACHINE,
  other: Equipment.OTHER,
  sled: Equipment.MACHINE,
  smith: Equipment.SMITH,
};

/** Decides which inputs the set logger shows for this exercise. */
function inferKind(entry: DatasetExercise): ExerciseKind {
  if (entry.category === 'cardio') return ExerciseKind.DISTANCE_DURATION;
  if (entry.category === 'stretching') return ExerciseKind.DURATION;
  if (entry.equipment === 'bodyweight') return ExerciseKind.BODYWEIGHT_REPS;
  return ExerciseKind.WEIGHT_REPS;
}

const toMuscle = (value: string): MuscleGroup => MUSCLE_MAP[value] ?? MuscleGroup.OTHER;

async function main(): Promise<void> {
  const configured = process.env.EXERCISES_DATASET;
  const datasetPath = configured
    ? isAbsolute(configured)
      ? configured
      : resolve(process.cwd(), configured)
    : DEFAULT_DATASET;

  const raw = await readFile(datasetPath, 'utf8');
  const parsed = JSON.parse(raw) as { exercises: DatasetExercise[] };
  const entries = parsed.exercises ?? [];

  console.log(`Seeding ${entries.length} exercises from ${datasetPath}`);

  const prisma = new PrismaClient();
  let processed = 0;

  try {
    // Chunked so one long transaction doesn't hold the pool for the whole run.
    const CHUNK = 100;
    for (let index = 0; index < entries.length; index += CHUNK) {
      const chunk = entries.slice(index, index + CHUNK);

      await prisma.$transaction(
        chunk.map((entry) => {
          const secondary = [
            ...new Set((entry.secondaryMuscles ?? []).map(toMuscle).filter((m) => m !== MuscleGroup.OTHER)),
          ];

          const data = {
            name: entry.name,
            muscleGroup: toMuscle(entry.muscle),
            secondaryMuscles: secondary,
            equipment: EQUIPMENT_MAP[entry.equipment] ?? Equipment.OTHER,
            kind: inferKind(entry),
            instructions: entry.instructions ?? [],
            imageUrl: entry.gifUrl ?? null,
            thumbUrl: entry.thumbUrl ?? null,
          };

          return prisma.exercise.upsert({
            where: { slug: entry.slug },
            // Never touch a user's custom exercise that happens to share a slug.
            create: { slug: entry.slug, ...data, createdById: null },
            update: data,
          });
        }),
      );

      processed += chunk.length;
      process.stdout.write(`\r  ${processed}/${entries.length}`);
    }

    process.stdout.write('\n');
    const total = await prisma.exercise.count({ where: { createdById: null } });
    console.log(`Done. Exercise library now holds ${total} built-in exercises.`);
  } finally {
    await prisma.$disconnect();
  }
}

main().catch((error: unknown) => {
  console.error('Seed failed:', error);
  process.exit(1);
});
