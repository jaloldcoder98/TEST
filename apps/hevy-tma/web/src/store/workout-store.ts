import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { DraftExercise, DraftSet, Exercise, SetType } from '../types';

const uid = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

const emptySet = (setType: SetType = 'NORMAL'): DraftSet => ({
  localId: uid(),
  setType,
  weightKg: null,
  reps: null,
  rpe: null,
  isCompleted: false,
  completedAt: null,
  previous: null,
});

export interface RestTimerState {
  /** Epoch ms when the rest period ends. */
  endsAt: number;
  durationSec: number;
}

interface WorkoutState {
  /** null when no workout is in progress. */
  startedAt: string | null;
  title: string;
  notes: string | null;
  exercises: DraftExercise[];
  restTimer: RestTimerState | null;

  startWorkout: (title?: string) => void;
  discardWorkout: () => void;
  setTitle: (title: string) => void;

  addExercises: (exercises: Exercise[], defaultRestSec: number) => void;
  removeExercise: (exerciseLocalId: string) => void;
  reorderExercise: (exerciseLocalId: string, direction: -1 | 1) => void;
  setExerciseNotes: (exerciseLocalId: string, notes: string) => void;
  setExerciseRest: (exerciseLocalId: string, restSeconds: number | null) => void;

  addSet: (exerciseLocalId: string) => void;
  removeSet: (exerciseLocalId: string, setLocalId: string) => void;
  updateSet: (exerciseLocalId: string, setLocalId: string, patch: Partial<DraftSet>) => void;
  toggleSetComplete: (exerciseLocalId: string, setLocalId: string) => boolean;
  cycleSetType: (exerciseLocalId: string, setLocalId: string) => void;

  startRest: (seconds: number) => void;
  adjustRest: (deltaSec: number) => void;
  stopRest: () => void;
}

const SET_TYPE_CYCLE: SetType[] = ['NORMAL', 'WARMUP', 'DROP', 'FAILURE'];

/** Map over one exercise, leaving the rest of the array untouched. */
const mapExercise = (
  exercises: DraftExercise[],
  localId: string,
  update: (exercise: DraftExercise) => DraftExercise,
): DraftExercise[] => exercises.map((item) => (item.localId === localId ? update(item) : item));

export const useWorkoutStore = create<WorkoutState>()(
  persist(
    (set, get) => ({
      startedAt: null,
      title: 'Workout',
      notes: null,
      exercises: [],
      restTimer: null,

      startWorkout: (title = 'Workout') =>
        set({ startedAt: new Date().toISOString(), title, notes: null, exercises: [], restTimer: null }),

      discardWorkout: () =>
        set({ startedAt: null, title: 'Workout', notes: null, exercises: [], restTimer: null }),

      setTitle: (title) => set({ title }),

      addExercises: (incoming, defaultRestSec) =>
        set((state) => ({
          // Adding an exercise implicitly starts a workout, so the user can
          // begin from the library without a separate "start" tap.
          startedAt: state.startedAt ?? new Date().toISOString(),
          exercises: [
            ...state.exercises,
            ...incoming.map((exercise) => ({
              localId: uid(),
              exercise,
              notes: null,
              restSeconds: defaultRestSec,
              sets: [emptySet()],
            })),
          ],
        })),

      removeExercise: (exerciseLocalId) =>
        set((state) => ({
          exercises: state.exercises.filter((item) => item.localId !== exerciseLocalId),
        })),

      reorderExercise: (exerciseLocalId, direction) =>
        set((state) => {
          const index = state.exercises.findIndex((item) => item.localId === exerciseLocalId);
          const target = index + direction;
          if (index === -1 || target < 0 || target >= state.exercises.length) return state;

          const exercises = [...state.exercises];
          const [moved] = exercises.splice(index, 1);
          if (moved) exercises.splice(target, 0, moved);
          return { exercises };
        }),

      setExerciseNotes: (exerciseLocalId, notes) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => ({
            ...exercise,
            notes: notes.trim() === '' ? null : notes,
          })),
        })),

      setExerciseRest: (exerciseLocalId, restSeconds) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => ({
            ...exercise,
            restSeconds,
          })),
        })),

      addSet: (exerciseLocalId) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => {
            // Carry the last set's load forward — that is what a lifter expects.
            const last = exercise.sets.at(-1);
            const next = emptySet();
            if (last) {
              next.weightKg = last.weightKg;
              next.reps = last.reps;
            }
            return { ...exercise, sets: [...exercise.sets, next] };
          }),
        })),

      removeSet: (exerciseLocalId, setLocalId) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => ({
            ...exercise,
            sets: exercise.sets.filter((item) => item.localId !== setLocalId),
          })),
        })),

      updateSet: (exerciseLocalId, setLocalId, patch) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => ({
            ...exercise,
            sets: exercise.sets.map((item) =>
              item.localId === setLocalId ? { ...item, ...patch } : item,
            ),
          })),
        })),

      /** Returns the set's new completed state so the caller can start rest. */
      toggleSetComplete: (exerciseLocalId, setLocalId) => {
        const exercise = get().exercises.find((item) => item.localId === exerciseLocalId);
        const target = exercise?.sets.find((item) => item.localId === setLocalId);
        const nowCompleted = !target?.isCompleted;

        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (item) => ({
            ...item,
            sets: item.sets.map((current) =>
              current.localId === setLocalId
                ? {
                    ...current,
                    isCompleted: nowCompleted,
                    completedAt: nowCompleted ? new Date().toISOString() : null,
                  }
                : current,
            ),
          })),
        }));

        return nowCompleted;
      },

      cycleSetType: (exerciseLocalId, setLocalId) =>
        set((state) => ({
          exercises: mapExercise(state.exercises, exerciseLocalId, (exercise) => ({
            ...exercise,
            sets: exercise.sets.map((item) => {
              if (item.localId !== setLocalId) return item;
              const next = SET_TYPE_CYCLE[(SET_TYPE_CYCLE.indexOf(item.setType) + 1) % SET_TYPE_CYCLE.length];
              return { ...item, setType: next ?? 'NORMAL' };
            }),
          })),
        })),

      startRest: (seconds) =>
        set({ restTimer: { endsAt: Date.now() + seconds * 1000, durationSec: seconds } }),

      adjustRest: (deltaSec) =>
        set((state) =>
          state.restTimer
            ? {
                restTimer: {
                  endsAt: Math.max(Date.now(), state.restTimer.endsAt + deltaSec * 1000),
                  durationSec: Math.max(0, state.restTimer.durationSec + deltaSec),
                },
              }
            : state,
        ),

      stopRest: () => set({ restTimer: null }),
    }),
    {
      // Telegram can suspend or reload the WebView at any moment; keeping the
      // draft in localStorage means a mid-workout reload costs nothing.
      name: 'hevy-tma:active-workout',
      partialize: (state) => ({
        startedAt: state.startedAt,
        title: state.title,
        notes: state.notes,
        exercises: state.exercises,
      }),
    },
  ),
);

/** Derived totals for the active workout header. */
export function selectTotals(state: WorkoutState): { volumeKg: number; sets: number } {
  let volumeKg = 0;
  let sets = 0;

  for (const exercise of state.exercises) {
    for (const item of exercise.sets) {
      if (!item.isCompleted || item.setType === 'WARMUP') continue;
      sets += 1;
      volumeKg += (item.weightKg ?? 0) * (item.reps ?? 0);
    }
  }

  return { volumeKg, sets };
}
