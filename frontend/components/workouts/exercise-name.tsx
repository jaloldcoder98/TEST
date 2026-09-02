"use client";

import { useExercise } from "@/lib/hooks/use-exercises";

/** Resolves a workout_exercise's exercise name/gif for display — WorkoutOut only carries
 * exercise_id (docs/API.md), so the workout list/detail views join against /exercises/{id}
 * per exercise rather than the backend denormalizing names onto every workout response. */
export function ExerciseName({ exerciseId, lang }: { exerciseId: string; lang: string }) {
  const exercise = useExercise(exerciseId, lang);
  if (exercise.isLoading) return <span className="text-muted-foreground">…</span>;
  return <>{exercise.data?.name ?? exerciseId}</>;
}

export function ExerciseThumb({ exerciseId, lang }: { exerciseId: string; lang: string }) {
  const exercise = useExercise(exerciseId, lang);
  if (!exercise.data) return <div className="h-12 w-12 rounded-lg bg-surface-2" />;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- external CDN GIF
    <img src={exercise.data.gif_url} alt={exercise.data.name} className="h-12 w-12 rounded-lg object-cover" />
  );
}
