"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useExercise } from "@/lib/hooks/use-exercises";
import { useLogSet } from "@/lib/hooks/use-workouts";
import type { WorkoutSet } from "@/lib/types";

export function SetLogger({
  sessionId,
  workoutExerciseId,
  exerciseId,
  lang,
  onSetLogged,
}: {
  sessionId: string;
  workoutExerciseId: string;
  exerciseId: string;
  lang: string;
  onSetLogged: (set: WorkoutSet) => void;
}) {
  const t = useTranslations("workouts");
  const exercise = useExercise(exerciseId, lang);
  const logSet = useLogSet(sessionId);

  const [loggedCount, setLoggedCount] = useState(0);
  const [reps, setReps] = useState("");
  const [weight, setWeight] = useState("");

  async function handleLog() {
    const setNumber = loggedCount + 1;
    const set = await logSet.mutateAsync({
      workout_exercise_id: workoutExerciseId,
      set_number: setNumber,
      reps: reps ? Number(reps) : undefined,
      weight_kg: weight ? Number(weight) : undefined,
      completed: true,
    });
    setLoggedCount(setNumber);
    onSetLogged(set as WorkoutSet);
    setReps("");
    setWeight("");
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center gap-3">
        {exercise.data && (
          // eslint-disable-next-line @next/next/no-img-element -- external CDN GIF
          <img src={exercise.data.gif_url} alt={exercise.data.name} className="h-10 w-10 rounded-lg object-cover" />
        )}
        <span className="font-semibold">{exercise.data?.name ?? "…"}</span>
        {loggedCount > 0 && (
          <span className="ml-auto rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary">
            {t("set")} {loggedCount}
          </span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1.5 block text-xs text-muted-foreground">{t("reps")}</label>
          <Input type="number" inputMode="numeric" value={reps} onChange={(e) => setReps(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="mb-1.5 block text-xs text-muted-foreground">{t("weight")}</label>
          <Input type="number" inputMode="decimal" step="0.5" value={weight} onChange={(e) => setWeight(e.target.value)} />
        </div>
        <Button type="button" onClick={handleLog} disabled={logSet.isPending}>
          <Check className="h-4 w-4" />
          {t("logSet")}
        </Button>
      </div>
    </div>
  );
}
