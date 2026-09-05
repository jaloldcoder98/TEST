import type { Exercise, Workout, WorkoutExercise, WorkoutSet } from '@prisma/client';
import { toNumber } from '../../lib/decimal.js';

type FullWorkout = Workout & {
  exercises: (WorkoutExercise & { exercise: Exercise; sets: WorkoutSet[] })[];
};

export const serializeSet = (set: WorkoutSet) => ({
  id: set.id,
  setNumber: set.setNumber,
  setType: set.setType,
  weightKg: toNumber(set.weightKg),
  reps: set.reps,
  rpe: toNumber(set.rpe),
  durationSec: set.durationSec,
  distanceM: toNumber(set.distanceM),
  isCompleted: set.isCompleted,
  completedAt: set.completedAt,
});

export const serializeWorkout = (workout: FullWorkout) => ({
  id: workout.id,
  title: workout.title,
  notes: workout.notes,
  status: workout.status,
  startedAt: workout.startedAt,
  finishedAt: workout.finishedAt,
  durationSec: workout.durationSec,
  totalVolumeKg: toNumber(workout.totalVolumeKg) ?? 0,
  totalSets: workout.totalSets,
  totalReps: workout.totalReps,
  exercises: workout.exercises.map((item) => ({
    id: item.id,
    position: item.position,
    notes: item.notes,
    restSeconds: item.restSeconds,
    exercise: {
      id: item.exercise.id,
      slug: item.exercise.slug,
      name: item.exercise.name,
      muscleGroup: item.exercise.muscleGroup,
      equipment: item.exercise.equipment,
      kind: item.exercise.kind,
      thumbUrl: item.exercise.thumbUrl,
    },
    sets: item.sets.map(serializeSet),
  })),
});

export type SerializedWorkout = ReturnType<typeof serializeWorkout>;
