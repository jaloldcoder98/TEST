import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { MUSCLE_LABELS } from '../lib/format';
import { haptic } from '../lib/telegram';
import type { Exercise, MuscleGroup } from '../types';
import { CheckIcon, CloseIcon, SearchIcon } from './icons';

interface ExercisePickerProps {
  onClose: () => void;
  onConfirm: (exercises: Exercise[]) => void;
}

/** Full-screen sheet for searching the exercise library and multi-selecting. */
export function ExercisePicker({ onClose, onConfirm }: ExercisePickerProps) {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [muscleGroup, setMuscleGroup] = useState<MuscleGroup | null>(null);
  const [selected, setSelected] = useState<Exercise[]>([]);

  // The library is 1300+ rows; don't hit the API on every keystroke.
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(search.trim()), 250);
    return () => window.clearTimeout(id);
  }, [search]);

  const groupsQuery = useQuery({
    queryKey: ['muscle-groups'],
    queryFn: () => api.muscleGroups(),
    staleTime: 60 * 60 * 1000,
  });

  const exercisesQuery = useQuery({
    queryKey: ['exercises', debounced, muscleGroup],
    queryFn: () =>
      api.listExercises({
        ...(debounced ? { q: debounced } : {}),
        ...(muscleGroup ? { muscleGroup } : {}),
        limit: 60,
      }),
    staleTime: 5 * 60 * 1000,
  });

  const selectedIds = useMemo(() => new Set(selected.map((item) => item.id)), [selected]);

  const toggle = (exercise: Exercise): void => {
    haptic.selection();
    setSelected((current) =>
      current.some((item) => item.id === exercise.id)
        ? current.filter((item) => item.id !== exercise.id)
        : [...current, exercise],
    );
  };

  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-tg-bg">
      <header className="border-b border-surface-line px-3 pb-3 pt-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon
              width={16}
              height={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tg-hint"
            />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Mashq qidirish…"
              autoFocus
              className="h-10 w-full rounded-xl bg-tg-secondary pl-9 pr-3 text-sm outline-none
                         placeholder:text-tg-hint focus:ring-1 focus:ring-accent"
            />
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Yopish"
            className="rounded-xl p-2 text-tg-hint active:scale-90"
          >
            <CloseIcon width={20} height={20} />
          </button>
        </div>

        {/* Muscle-group filter chips */}
        <div className="-mx-3 mt-3 flex gap-2 overflow-x-auto px-3 pb-1">
          <Chip active={muscleGroup === null} onClick={() => setMuscleGroup(null)}>
            Barchasi
          </Chip>
          {groupsQuery.data?.items.map((group) => (
            <Chip
              key={group.muscleGroup}
              active={muscleGroup === group.muscleGroup}
              onClick={() => setMuscleGroup(group.muscleGroup as MuscleGroup)}
            >
              {MUSCLE_LABELS[group.muscleGroup as MuscleGroup]} · {group.count}
            </Chip>
          ))}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {exercisesQuery.isPending && <p className="py-8 text-center text-sm text-tg-hint">Yuklanmoqda…</p>}

        {exercisesQuery.isError && (
          <p className="py-8 text-center text-sm text-tg-destructive">
            Mashqlarni yuklab bo'lmadi. Qayta urinib ko'ring.
          </p>
        )}

        {exercisesQuery.data?.items.length === 0 && (
          <p className="py-8 text-center text-sm text-tg-hint">Hech narsa topilmadi.</p>
        )}

        <ul className="space-y-1">
          {exercisesQuery.data?.items.map((exercise) => {
            const isSelected = selectedIds.has(exercise.id);
            return (
              <li key={exercise.id}>
                <button
                  type="button"
                  onClick={() => toggle(exercise)}
                  className={`flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors
                              ${isSelected ? 'bg-accent-soft' : 'active:bg-surface-raised'}`}
                >
                  {exercise.thumbUrl ? (
                    <img
                      src={exercise.thumbUrl}
                      alt=""
                      loading="lazy"
                      className="h-11 w-11 shrink-0 rounded-lg bg-surface-raised object-cover"
                    />
                  ) : (
                    <div className="h-11 w-11 shrink-0 rounded-lg bg-surface-raised" aria-hidden />
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{exercise.name}</div>
                    <div className="text-xs text-tg-hint">
                      {MUSCLE_LABELS[exercise.muscleGroup]} · {exercise.equipment.toLowerCase()}
                    </div>
                  </div>

                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full
                                ${isSelected ? 'bg-accent text-white' : 'ring-1 ring-inset ring-surface-strong'}`}
                  >
                    {isSelected && <CheckIcon width={13} height={13} />}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <footer className="border-t border-surface-line p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))]">
        <button
          type="button"
          disabled={selected.length === 0}
          onClick={() => onConfirm(selected)}
          className="w-full rounded-2xl bg-accent py-3.5 text-[15px] font-semibold text-white
                     disabled:opacity-40 active:scale-[0.99]"
        >
          {selected.length === 0 ? 'Mashq tanlang' : `Qo'shish (${selected.length})`}
        </button>
      </footer>
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`shrink-0 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition-colors
                  ${active ? 'bg-accent text-white' : 'bg-tg-secondary text-tg-hint'}`}
    >
      {children}
    </button>
  );
}
