import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useElapsed } from '../hooks/useElapsed';
import { useRestTimer } from '../hooks/useRestTimer';
import { api, ApiError, type CreateWorkoutPayload } from '../lib/api';
import { formatDuration, formatVolume, PR_LABELS } from '../lib/format';
import { confirmDialog, haptic, setMainButton } from '../lib/telegram';
import { selectTotals, useWorkoutStore } from '../store/workout-store';
import type { CurrentUser, PersonalRecordHit } from '../types';
import { ExerciseCard } from './ExerciseCard';
import { ExercisePicker } from './ExercisePicker';
import { RestTimerBar } from './RestTimerBar';
import { DumbbellIcon, PlusIcon, TrophyIcon } from './icons';

interface WorkoutTrackerProps {
  user: CurrentUser;
}

/**
 * The active-workout screen: a Hevy-style list of exercises, each with its own
 * set rows (weight / reps / RPE + a checkmark), a rest timer that starts when a
 * set is completed, and Telegram's MainButton wired to "finish workout".
 */
export function WorkoutTracker({ user }: WorkoutTrackerProps) {
  const queryClient = useQueryClient();
  const timer = useRestTimer();

  const startedAt = useWorkoutStore((state) => state.startedAt);
  const title = useWorkoutStore((state) => state.title);
  const exercises = useWorkoutStore((state) => state.exercises);
  const startWorkout = useWorkoutStore((state) => state.startWorkout);
  const discardWorkout = useWorkoutStore((state) => state.discardWorkout);
  const setTitle = useWorkoutStore((state) => state.setTitle);
  const addExercises = useWorkoutStore((state) => state.addExercises);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [prBanner, setPrBanner] = useState<PersonalRecordHit[] | null>(null);

  const elapsed = useElapsed(startedAt);
  const totals = useWorkoutStore(selectTotals);

  const completedSets = useMemo(
    () => exercises.reduce((sum, item) => sum + item.sets.filter((set) => set.isCompleted).length, 0),
    [exercises],
  );

  const saveMutation = useMutation({
    mutationFn: async (): Promise<{ personalRecords: PersonalRecordHit[] }> => {
      if (!startedAt) throw new Error('No workout in progress');

      const finishedAt = new Date();
      const payload: CreateWorkoutPayload = {
        title,
        status: 'COMPLETED',
        startedAt,
        finishedAt: finishedAt.toISOString(),
        durationSec: Math.max(0, Math.round((finishedAt.getTime() - new Date(startedAt).getTime()) / 1000)),
        exercises: exercises
          // Sets nobody completed are noise; drop them, and drop any exercise
          // left empty as a result. The API rejects an exercise with zero sets.
          .map((draft) => ({
            exerciseId: draft.exercise.id,
            notes: draft.notes,
            restSeconds: draft.restSeconds,
            sets: draft.sets
              .filter((set) => set.isCompleted)
              .map((set) => ({
                setType: set.setType,
                weightKg: set.weightKg,
                reps: set.reps,
                rpe: set.rpe,
                isCompleted: true,
                completedAt: set.completedAt,
              })),
          }))
          .filter((draft) => draft.sets.length > 0),
      };

      if (payload.exercises.length === 0) {
        throw new Error('Kamida bitta setni yakunlang');
      }

      return api.createWorkout(payload);
    },
    onSuccess: ({ personalRecords }) => {
      haptic.success();
      void queryClient.invalidateQueries({ queryKey: ['workouts'] });
      void queryClient.invalidateQueries({ queryKey: ['stats'] });
      discardWorkout();
      timer.skip();
      if (personalRecords.length > 0) setPrBanner(personalRecords);
    },
    onError: () => haptic.warning(),
  });

  const handleFinish = useCallback(async () => {
    if (completedSets === 0) {
      haptic.warning();
      return;
    }
    const confirmed = await confirmDialog(`Mashg'ulotni yakunlaysizmi? (${completedSets} set)`);
    if (confirmed) saveMutation.mutate();
  }, [completedSets, saveMutation]);

  // Telegram's native MainButton is the primary action while a workout is live.
  useEffect(() => {
    if (!startedAt || exercises.length === 0) return undefined;

    return setMainButton({
      text: saveMutation.isPending ? 'Saqlanmoqda…' : `Yakunlash (${completedSets} set)`,
      onClick: () => void handleFinish(),
      enabled: completedSets > 0 && !saveMutation.isPending,
      progress: saveMutation.isPending,
    });
  }, [startedAt, exercises.length, completedSets, saveMutation.isPending, handleFinish]);

  const handleDiscard = async (): Promise<void> => {
    const confirmed = await confirmDialog("Mashg'ulotni bekor qilasizmi? Kiritilgan ma'lumotlar o'chadi.");
    if (confirmed) {
      discardWorkout();
      timer.skip();
    }
  };

  // ---------------------------------------------------------------- empty state
  if (!startedAt || exercises.length === 0) {
    return (
      <>
        <div className="flex min-h-full flex-col items-center justify-center px-8 text-center">
          <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-accent-soft text-accent">
            <DumbbellIcon width={36} height={36} />
          </div>
          <h2 className="text-xl font-bold">Mashg'ulotni boshlang</h2>
          <p className="mt-2 max-w-xs text-sm text-tg-hint">
            Mashq tanlang, setlarni kiriting va har bir setdan keyin dam olish taymeri avtomatik
            ishga tushadi.
          </p>
          <button
            type="button"
            onClick={() => {
              haptic.impact('medium');
              if (!startedAt) startWorkout(`Workout · ${new Date().toLocaleDateString('uz-UZ')}`);
              setPickerOpen(true);
            }}
            className="mt-7 flex items-center gap-2 rounded-2xl bg-accent px-6 py-3.5
                       text-[15px] font-semibold text-white active:scale-95"
          >
            <PlusIcon width={18} height={18} />
            Mashq qo'shish
          </button>
        </div>

        {pickerOpen && (
          <ExercisePicker
            onClose={() => setPickerOpen(false)}
            onConfirm={(selected) => {
              addExercises(selected, user.defaultRestSeconds);
              setPickerOpen(false);
            }}
          />
        )}
      </>
    );
  }

  // ---------------------------------------------------------------- active workout
  return (
    <>
      <div className="flex min-h-full flex-col">
        <header className="sticky top-0 z-10 border-b border-surface-line bg-tg-bg px-4 py-3 backdrop-blur">
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full bg-transparent text-lg font-bold text-tg-text outline-none"
            aria-label="Mashg'ulot nomi"
          />

          <div className="mt-2 grid grid-cols-3 gap-2 text-center">
            <Stat label="Vaqt" value={formatDuration(elapsed)} />
            <Stat label="Hajm" value={formatVolume(totals.volumeKg)} />
            <Stat label="Setlar" value={String(totals.sets)} />
          </div>
        </header>

        <div className="flex-1 space-y-3 px-3 pb-4 pt-3">
          {exercises.map((draft) => (
            <ExerciseCard
              key={draft.localId}
              draft={draft}
              onSetCompleted={(restSeconds) => timer.start(restSeconds)}
            />
          ))}

          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed
                       border-surface-strong py-3.5 text-sm font-semibold text-accent active:scale-[0.99]"
          >
            <PlusIcon width={18} height={18} />
            Mashq qo'shish
          </button>

          <button
            type="button"
            onClick={() => void handleDiscard()}
            className="w-full rounded-2xl py-3 text-sm font-semibold text-tg-destructive active:scale-[0.99]"
          >
            Mashg'ulotni bekor qilish
          </button>

          {saveMutation.isError && (
            <p className="rounded-xl bg-rose-500/10 px-3 py-2 text-center text-sm text-tg-destructive">
              {saveMutation.error instanceof ApiError
                ? saveMutation.error.message
                : String(saveMutation.error)}
            </p>
          )}

          {/* Fallback for browsers where the Telegram MainButton is unavailable. */}
          <button
            type="button"
            onClick={() => void handleFinish()}
            disabled={completedSets === 0 || saveMutation.isPending}
            className="w-full rounded-2xl bg-accent py-3.5 text-[15px] font-semibold text-white
                       disabled:opacity-40 active:scale-[0.99]"
          >
            {saveMutation.isPending ? 'Saqlanmoqda…' : `Yakunlash (${completedSets} set)`}
          </button>
        </div>
      </div>

      <div className="pointer-events-none fixed inset-x-0 bottom-[calc(3.75rem+env(safe-area-inset-bottom,0px))] z-20">
        <RestTimerBar timer={timer} />
      </div>

      {pickerOpen && (
        <ExercisePicker
          onClose={() => setPickerOpen(false)}
          onConfirm={(selected) => {
            addExercises(selected, user.defaultRestSeconds);
            setPickerOpen(false);
          }}
        />
      )}

      {prBanner && <PersonalRecordToast records={prBanner} onDismiss={() => setPrBanner(null)} />}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-tg-secondary py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-tg-hint">{label}</div>
      <div className="text-base font-bold tabular-nums">{value}</div>
    </div>
  );
}

function PersonalRecordToast({
  records,
  onDismiss,
}: {
  records: PersonalRecordHit[];
  onDismiss: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-end bg-black/60 p-4" onClick={onDismiss}>
      <div
        className="w-full rounded-2xl bg-tg-secondary p-5"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-2 text-amber-400">
          <TrophyIcon width={22} height={22} />
          <h3 className="text-lg font-bold">Yangi rekord!</h3>
        </div>

        <ul className="mt-3 space-y-2">
          {records.slice(0, 6).map((record) => (
            <li key={`${record.exerciseId}-${record.type}`} className="text-sm">
              <span className="font-semibold">{record.exerciseName}</span>
              <span className="text-tg-hint"> · {PR_LABELS[record.type]}: </span>
              <span className="font-bold tabular-nums text-success">{record.value}</span>
              {record.previousValue != null && (
                <span className="text-tg-hint"> (oldin {record.previousValue})</span>
              )}
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={onDismiss}
          className="mt-4 w-full rounded-xl bg-accent py-3 font-semibold text-white active:scale-95"
        >
          Ajoyib
        </button>
      </div>
    </div>
  );
}
