"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Flag, Trophy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { FullPageSpinner } from "@/components/ui/spinner";
import { SetLogger } from "@/components/workouts/set-logger";
import { useFinishSession, useStartWorkout, useWorkout } from "@/lib/hooks/use-workouts";
import type { Locale } from "@/i18n";
import type { WorkoutSession, WorkoutSet } from "@/lib/types";

// There's no "resume an in-progress session" endpoint on the backend (docs/API.md) — a fresh
// page load here always starts a brand new session. That's an intentional, documented limit
// rather than a silently-lossy resume, and matches the API surface as it exists today.
export default function WorkoutSessionPage() {
  const t = useTranslations("workouts");
  const tc = useTranslations("common");
  const params = useParams();
  const locale = params.locale as Locale;
  const workoutId = params.id as string;

  const workout = useWorkout(workoutId);
  const startWorkout = useStartWorkout();
  const finishSession = useFinishSession();

  const [session, setSession] = useState<WorkoutSession | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    startWorkout.mutate(workoutId, { onSuccess: (s) => setSession(s) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workoutId]);

  function handleSetLogged(set: WorkoutSet) {
    setSession((prev) => (prev ? { ...prev, sets: [...prev.sets, set] } : prev));
  }

  async function handleFinish() {
    if (!session) return;
    const finished = await finishSession.mutateAsync(session.id);
    setSession(finished);
  }

  if (workout.isLoading || !session) return <FullPageSpinner />;
  const w = workout.data;
  if (!w) return null;

  if (session.status === "completed") {
    return (
      <div className="mx-auto max-w-md space-y-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Trophy className="h-8 w-8" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sessionFinished")}</h1>
        <Card className="text-left">
          <CardTitle className="mb-4">{t("summary")}</CardTitle>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{t("totalVolume")}</dt>
              <dd className="font-semibold">
                {session.total_volume_kg} {tc("kg")}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{t("totalSets")}</dt>
              <dd className="font-semibold">{session.total_sets}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{t("totalReps")}</dt>
              <dd className="font-semibold">{session.total_reps}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{t("caloriesBurned")}</dt>
              <dd className="font-semibold">
                {session.estimated_calories} {tc("kcal")}
              </dd>
            </div>
          </dl>
        </Card>
        <Button asChild size="lg" className="w-full">
          <Link href={`/${locale}/workouts`}>{t("backToWorkouts")}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{w.name}</h1>
          <p className="text-sm text-primary">{t("sessionInProgress")}</p>
        </div>
        <Button onClick={handleFinish} disabled={finishSession.isPending}>
          <Flag className="h-4 w-4" />
          {t("finishSession")}
        </Button>
      </div>

      <div className="space-y-3">
        {w.exercises.map((we) => (
          <SetLogger
            key={we.id}
            sessionId={session.id}
            workoutExerciseId={we.id}
            exerciseId={we.exercise_id}
            lang={locale}
            onSetLogged={handleSetLogged}
          />
        ))}
      </div>
    </div>
  );
}
