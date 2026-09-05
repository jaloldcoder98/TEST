import { SetType, WorkoutStatus } from '@prisma/client';
import { z } from 'zod';

/** RPE is 0–10 in half-point steps. */
const rpe = z
  .number()
  .min(0)
  .max(10)
  .refine((value) => Number.isInteger(value * 2), { message: 'RPE must be in 0.5 steps' });

export const setInputSchema = z.object({
  setType: z.nativeEnum(SetType).default(SetType.NORMAL),
  weightKg: z.number().min(0).max(1000).nullish(),
  reps: z.number().int().min(0).max(1000).nullish(),
  rpe: rpe.nullish(),
  durationSec: z.number().int().min(0).max(86_400).nullish(),
  distanceM: z.number().min(0).max(1_000_000).nullish(),
  isCompleted: z.boolean().default(true),
  completedAt: z.coerce.date().nullish(),
});

export const workoutExerciseInputSchema = z.object({
  exerciseId: z.string().uuid(),
  notes: z.string().max(1000).nullish(),
  restSeconds: z.number().int().min(0).max(3600).nullish(),
  sets: z.array(setInputSchema).min(1, 'An exercise needs at least one set').max(50),
});

export const createWorkoutSchema = z
  .object({
    title: z.string().trim().min(1).max(120).default('Workout'),
    notes: z.string().max(4000).nullish(),
    status: z.nativeEnum(WorkoutStatus).default(WorkoutStatus.COMPLETED),
    startedAt: z.coerce.date(),
    finishedAt: z.coerce.date().nullish(),
    /** Client-measured duration; falls back to finishedAt - startedAt. */
    durationSec: z.number().int().min(0).max(86_400).nullish(),
    exercises: z.array(workoutExerciseInputSchema).min(1, 'A workout needs at least one exercise').max(40),
  })
  .refine((value) => !value.finishedAt || value.finishedAt >= value.startedAt, {
    message: 'finishedAt must not be before startedAt',
    path: ['finishedAt'],
  });

export const listWorkoutsQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(50).default(20),
  cursor: z.string().uuid().optional(),
  status: z.nativeEnum(WorkoutStatus).optional(),
});

export type SetInput = z.infer<typeof setInputSchema>;
export type WorkoutExerciseInput = z.infer<typeof workoutExerciseInputSchema>;
export type CreateWorkoutInput = z.infer<typeof createWorkoutSchema>;
export type ListWorkoutsQuery = z.infer<typeof listWorkoutsQuerySchema>;
