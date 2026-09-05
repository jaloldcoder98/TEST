import { useMemo } from 'react';
import { MUSCLE_LABELS } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useWorkoutStore } from '../store/workout-store';
import type { DraftExercise } from '../types';
import { SetRow } from './SetRow';
import { PlusIcon, TimerIcon, TrashIcon } from './icons';

interface ExerciseCardProps {
  draft: DraftExercise;
  /** Called when a set is checked off, so the parent can start the rest timer. */
  onSetCompleted: (restSeconds: number) => void;
}

const REST_PRESETS = [60, 90, 120, 180];

export function ExerciseCard({ draft, onSetCompleted }: ExerciseCardProps) {
  const addSet = useWorkoutStore((state) => state.addSet);
  const removeSet = useWorkoutStore((state) => state.removeSet);
  const updateSet = useWorkoutStore((state) => state.updateSet);
  const toggleSetComplete = useWorkoutStore((state) => state.toggleSetComplete);
  const cycleSetType = useWorkoutStore((state) => state.cycleSetType);
  const removeExercise = useWorkoutStore((state) => state.removeExercise);
  const setExerciseRest = useWorkoutStore((state) => state.setExerciseRest);
  const setExerciseNotes = useWorkoutStore((state) => state.setExerciseNotes);

  // Warm-ups render as "W" and don't consume a working-set number.
  const workingIndexes = useMemo(() => {
    let counter = 0;
    return draft.sets.map((set) => (set.setType === 'WARMUP' ? 0 : (counter += 1)));
  }, [draft.sets]);

  const handleToggle = (setLocalId: string): void => {
    const nowCompleted = toggleSetComplete(draft.localId, setLocalId);
    if (nowCompleted && draft.restSeconds && draft.restSeconds > 0) {
      onSetCompleted(draft.restSeconds);
    }
  };

  return (
    <section className="card space-y-3">
      <header className="flex items-start gap-3">
        {draft.exercise.thumbUrl ? (
          <img
            src={draft.exercise.thumbUrl}
            alt=""
            loading="lazy"
            className="h-11 w-11 shrink-0 rounded-lg bg-surface-raised object-cover"
          />
        ) : (
          <div className="h-11 w-11 shrink-0 rounded-lg bg-surface-raised" aria-hidden />
        )}

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-[15px] font-semibold leading-tight text-accent">
            {draft.exercise.name}
          </h3>
          <p className="mt-0.5 text-xs text-tg-hint">
            {MUSCLE_LABELS[draft.exercise.muscleGroup]} · {draft.exercise.equipment.toLowerCase()}
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            haptic.warning();
            removeExercise(draft.localId);
          }}
          aria-label="Mashqni o'chirish"
          className="rounded-lg p-2 text-tg-hint active:scale-90"
        >
          <TrashIcon width={16} height={16} />
        </button>
      </header>

      <input
        type="text"
        placeholder="Izoh qo'shish…"
        defaultValue={draft.notes ?? ''}
        onBlur={(event) => setExerciseNotes(draft.localId, event.target.value)}
        className="w-full rounded-lg bg-surface-sunken px-3 py-2 text-sm text-tg-text
                   outline-none placeholder:text-tg-hint focus:ring-1 focus:ring-accent"
      />

      {/* Rest preference for this exercise */}
      <div className="flex items-center gap-1.5 text-xs">
        <TimerIcon width={14} height={14} className="text-tg-hint" />
        {REST_PRESETS.map((seconds) => (
          <button
            key={seconds}
            type="button"
            onClick={() => {
              haptic.selection();
              setExerciseRest(draft.localId, seconds);
            }}
            className={`rounded-full px-2.5 py-1 font-medium transition-colors
                        ${
                          draft.restSeconds === seconds
                            ? 'bg-accent text-white'
                            : 'bg-surface-raised text-tg-hint'
                        }`}
          >
            {seconds < 60 ? `${seconds}s` : `${seconds / 60}m`}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setExerciseRest(draft.localId, null)}
          className={`rounded-full px-2.5 py-1 font-medium transition-colors
                      ${draft.restSeconds === null ? 'bg-accent text-white' : 'bg-surface-raised text-tg-hint'}`}
        >
          Off
        </button>
      </div>

      {/* Column headers */}
      <div
        className="grid grid-cols-[2.25rem_3.5rem_1fr_1fr_3.25rem_2.5rem] gap-2 px-1
                   text-[10px] font-semibold uppercase tracking-wide text-tg-hint"
      >
        <span className="text-center">Set</span>
        <span className="text-center">Oldingi</span>
        <span className="text-center">Kg</span>
        <span className="text-center">Takror</span>
        <span className="text-center">RPE</span>
        <span aria-hidden />
      </div>

      <div className="space-y-1">
        {draft.sets.map((set, index) => (
          <SetRow
            key={set.localId}
            set={set}
            workingIndex={workingIndexes[index] ?? index + 1}
            onChange={(patch) => updateSet(draft.localId, set.localId, patch)}
            onToggleComplete={() => handleToggle(set.localId)}
            onCycleType={() => cycleSetType(draft.localId, set.localId)}
            onRemove={() => removeSet(draft.localId, set.localId)}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={() => {
          haptic.impact('light');
          addSet(draft.localId);
        }}
        className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-surface-raised py-2.5
                   text-sm font-semibold text-tg-text active:scale-[0.99]"
      >
        <PlusIcon width={16} height={16} />
        Set qo'shish
      </button>
    </section>
  );
}
