"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useTranslations } from "next-intl";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useExercises } from "@/lib/hooks/use-exercises";
import { useCreateWorkout } from "@/lib/hooks/use-workouts";
import type { Locale } from "@/i18n";

interface DraftExercise {
  exercise_id: string;
  name: string;
}

export function CreateWorkoutDialog() {
  const t = useTranslations("workouts");
  const tc = useTranslations("common");
  const params = useParams();
  const locale = params.locale as Locale;
  const router = useRouter();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [day, setDay] = useState("");
  const [draftExercises, setDraftExercises] = useState<DraftExercise[]>([]);
  const [selectedExerciseId, setSelectedExerciseId] = useState("");

  const exercises = useExercises({ lang: locale });
  const createWorkout = useCreateWorkout();

  function addExercise() {
    if (!selectedExerciseId) return;
    const found = exercises.data?.items.find((e) => e.id === selectedExerciseId);
    if (!found || draftExercises.some((d) => d.exercise_id === found.id)) return;
    setDraftExercises((prev) => [...prev, { exercise_id: found.id, name: found.name }]);
    setSelectedExerciseId("");
  }

  function removeExercise(exerciseId: string) {
    setDraftExercises((prev) => prev.filter((d) => d.exercise_id !== exerciseId));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const workout = await createWorkout.mutateAsync({
      name,
      description: description || undefined,
      day: day || undefined,
      exercises: draftExercises.map((d, i) => ({ exercise_id: d.exercise_id, order: i })),
    });
    setOpen(false);
    setName("");
    setDescription("");
    setDay("");
    setDraftExercises([]);
    router.push(`/${locale}/workouts/${workout.id}`);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button>
          <Plus className="h-4 w-4" />
          {t("createButton")}
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-border bg-surface p-6">
          <div className="mb-5 flex items-center justify-between">
            <Dialog.Title className="text-lg font-bold">{t("createButton")}</Dialog.Title>
            <Dialog.Close asChild>
              <button aria-label={tc("close")} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="w-name">{t("name")}</Label>
              <Input id="w-name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="w-desc">
                {t("description")} <span className="text-muted-foreground">({tc("optional")})</span>
              </Label>
              <Textarea id="w-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="w-day">
                {t("day")} <span className="text-muted-foreground">({tc("optional")})</span>
              </Label>
              <Input id="w-day" value={day} onChange={(e) => setDay(e.target.value)} placeholder={t("dayPlaceholder")} />
            </div>

            <div>
              <Label>{t("addExercise")}</Label>
              <div className="flex gap-2">
                <Select value={selectedExerciseId} onChange={(e) => setSelectedExerciseId(e.target.value)}>
                  <option value="">{t("selectExercise")}</option>
                  {exercises.data?.items.map((ex) => (
                    <option key={ex.id} value={ex.id}>
                      {ex.name}
                    </option>
                  ))}
                </Select>
                <Button type="button" variant="secondary" onClick={addExercise}>
                  {tc("add")}
                </Button>
              </div>
            </div>

            {draftExercises.length > 0 && (
              <ul className="space-y-2">
                {draftExercises.map((d, i) => (
                  <li
                    key={d.exercise_id}
                    className="flex items-center justify-between rounded-xl border border-border bg-surface-2 px-3 py-2 text-sm"
                  >
                    <span>
                      {i + 1}. {d.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeExercise(d.exercise_id)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <Button type="submit" className="w-full" disabled={createWorkout.isPending || !name}>
              {tc("save")}
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
