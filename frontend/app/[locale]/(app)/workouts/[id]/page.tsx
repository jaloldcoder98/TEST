"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { FullPageSpinner } from "@/components/ui/spinner";
import { ExerciseName, ExerciseThumb } from "@/components/workouts/exercise-name";
import { ApiError } from "@/lib/api-client";
import { useDeleteWorkout, useWorkout } from "@/lib/hooks/use-workouts";
import type { Locale } from "@/i18n";

export default function WorkoutDetailPage() {
  const t = useTranslations("workouts");
  const tc = useTranslations("common");
  const params = useParams();
  const router = useRouter();
  const locale = params.locale as Locale;
  const id = params.id as string;

  const workout = useWorkout(id);
  const deleteWorkout = useDeleteWorkout();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  async function handleDelete() {
    setDeleteError(null);
    try {
      await deleteWorkout.mutateAsync(id);
      router.push(`/${locale}/workouts`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "WORKOUT_HAS_HISTORY") {
        setDeleteError(t("cannotDeleteHasHistory"));
      } else {
        setDeleteError(tc("error"));
      }
      setConfirmingDelete(false);
    }
  }

  if (workout.isLoading) return <FullPageSpinner />;
  if (!workout.data) return null;

  const w = workout.data;

  return (
    <div className="space-y-6">
      <Link href={`/${locale}/workouts`} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        {t("backToWorkouts")}
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{w.name}</h1>
          {w.description && <p className="mt-1 text-muted-foreground">{w.description}</p>}
        </div>
        <div className="flex gap-2">
          <Button asChild size="lg">
            <Link href={`/${locale}/workouts/${w.id}/session`}>
              <Play className="h-4 w-4" />
              {t("start")}
            </Link>
          </Button>
        </div>
      </div>

      {w.exercises.length > 0 ? (
        <ul className="space-y-2">
          {w.exercises.map((we, i) => (
            <li key={we.id} className="flex items-center gap-4 rounded-xl border border-border bg-surface p-3">
              <span className="w-5 text-sm font-semibold text-muted-foreground">{i + 1}</span>
              <ExerciseThumb exerciseId={we.exercise_id} lang={locale} />
              <span className="font-medium">
                <ExerciseName exerciseId={we.exercise_id} lang={locale} />
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{t("noExercisesYet")}</p>
      )}

      <div className="border-t border-border pt-6">
        {confirmingDelete ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted-foreground">{t("deleteConfirm")}</p>
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteWorkout.isPending}>
              {t("delete")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(false)}>
              {tc("cancel")}
            </Button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmingDelete(true)}
            className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            {t("delete")}
          </button>
        )}
        {deleteError && <p className="mt-2 text-sm text-destructive">{deleteError}</p>}
      </div>
    </div>
  );
}
