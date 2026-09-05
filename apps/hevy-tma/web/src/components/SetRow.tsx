import { memo, useCallback } from 'react';
import { SET_TYPE_COLORS, setLabel } from '../lib/format';
import { haptic } from '../lib/telegram';
import type { DraftSet } from '../types';
import { CheckIcon } from './icons';

interface SetRowProps {
  set: DraftSet;
  /** 1-based index among working sets; warm-ups don't consume a number. */
  workingIndex: number;
  onChange: (patch: Partial<DraftSet>) => void;
  onToggleComplete: () => void;
  onCycleType: () => void;
  onRemove: () => void;
}

/** Parse a numeric input, treating an empty field as "not entered". */
const parseNumber = (raw: string): number | null => {
  const normalized = raw.replace(',', '.').trim();
  if (normalized === '') return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
};

function SetRowComponent({
  set,
  workingIndex,
  onChange,
  onToggleComplete,
  onCycleType,
  onRemove,
}: SetRowProps) {
  const handleToggle = useCallback(() => {
    haptic.impact('medium');
    onToggleComplete();
  }, [onToggleComplete]);

  const handleCycleType = useCallback(() => {
    haptic.selection();
    onCycleType();
  }, [onCycleType]);

  const previous = set.previous;
  const previousLabel =
    previous?.weightKg != null && previous.reps != null
      ? `${previous.weightKg} × ${previous.reps}`
      : '—';

  return (
    <div
      className={`grid grid-cols-[2.25rem_3.5rem_1fr_1fr_3.25rem_2.5rem] items-center gap-2
                  rounded-xl px-1 py-1.5 transition-colors
                  ${set.isCompleted ? 'bg-success/10' : 'bg-transparent'}`}
    >
      {/* Set number — tap to cycle warm-up / normal / drop / failure */}
      <button
        type="button"
        onClick={handleCycleType}
        aria-label="Set turini o'zgartirish"
        className={`h-9 rounded-lg text-sm font-bold tabular-nums transition-colors
                    active:scale-95 ${SET_TYPE_COLORS[set.setType]}`}
      >
        {setLabel(set.setType, workingIndex)}
      </button>

      {/* Last time's numbers, shown for reference */}
      <span className="truncate text-center text-xs tabular-nums text-tg-hint">{previousLabel}</span>

      <input
        type="number"
        inputMode="decimal"
        step="0.5"
        min="0"
        className="set-input"
        placeholder={previous?.weightKg != null ? String(previous.weightKg) : '0'}
        value={set.weightKg ?? ''}
        onChange={(event) => onChange({ weightKg: parseNumber(event.target.value) })}
        aria-label="Og'irlik (kg)"
      />

      <input
        type="number"
        inputMode="numeric"
        step="1"
        min="0"
        className="set-input"
        placeholder={previous?.reps != null ? String(previous.reps) : '0'}
        value={set.reps ?? ''}
        onChange={(event) => onChange({ reps: parseNumber(event.target.value) })}
        aria-label="Takrorlashlar"
      />

      <input
        type="number"
        inputMode="decimal"
        step="0.5"
        min="0"
        max="10"
        className="set-input text-[13px]"
        placeholder="RPE"
        value={set.rpe ?? ''}
        onChange={(event) => {
          const value = parseNumber(event.target.value);
          // Clamp rather than reject: the server enforces the same 0–10 range.
          onChange({ rpe: value === null ? null : Math.min(10, Math.max(0, value)) });
        }}
        aria-label="RPE (0-10)"
      />

      {/* Checkmark — the "finish this set" action */}
      <button
        type="button"
        onClick={handleToggle}
        onContextMenu={(event) => {
          event.preventDefault();
          onRemove();
        }}
        aria-pressed={set.isCompleted}
        aria-label={set.isCompleted ? 'Setni bekor qilish' : 'Setni yakunlash'}
        className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all active:scale-90
                    ${
                      set.isCompleted
                        ? 'bg-success text-white'
                        : 'bg-surface-raised text-tg-hint ring-1 ring-inset ring-surface-line'
                    }`}
      >
        <CheckIcon width={16} height={16} />
      </button>
    </div>
  );
}

export const SetRow = memo(SetRowComponent);
