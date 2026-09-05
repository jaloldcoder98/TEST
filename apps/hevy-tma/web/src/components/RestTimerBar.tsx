import { formatDuration } from '../lib/format';
import { haptic } from '../lib/telegram';
import type { RestTimer } from '../hooks/useRestTimer';

interface RestTimerBarProps {
  timer: RestTimer;
}

/**
 * Sticky bar above the bottom navigation showing the rest countdown,
 * with -15s / +15s adjustments and a skip.
 */
export function RestTimerBar({ timer }: RestTimerBarProps) {
  if (!timer.active) return null;

  const finished = timer.remainingSec === 0;

  const adjust = (delta: number): void => {
    haptic.selection();
    timer.add(delta);
  };

  return (
    <div className="pointer-events-auto px-3 pb-2">
      <div
        className={`relative overflow-hidden rounded-2xl bg-tg-secondary shadow-lg ring-1
                    ${finished ? 'ring-success/60' : 'ring-surface-line'}`}
      >
        {/* Progress fill drains left-to-right as the rest elapses. */}
        <div
          className={`absolute inset-y-0 left-0 transition-[width] duration-300 ease-linear
                      ${finished ? 'bg-success/25' : 'bg-accent/20'}`}
          style={{ width: `${Math.min(100, timer.progress * 100)}%` }}
          aria-hidden
        />

        <div className="relative flex items-center gap-2 px-3 py-2.5">
          <button
            type="button"
            onClick={() => adjust(-15)}
            className="h-9 w-11 rounded-lg bg-surface-raised text-sm font-semibold text-tg-text active:scale-95"
          >
            −15
          </button>

          <div className="flex-1 text-center">
            <div className="text-[11px] uppercase tracking-wide text-tg-hint">
              {finished ? 'Dam tugadi' : 'Dam olish'}
            </div>
            <div className="text-2xl font-bold tabular-nums leading-tight">
              {formatDuration(timer.remainingSec)}
            </div>
          </div>

          <button
            type="button"
            onClick={() => adjust(15)}
            className="h-9 w-11 rounded-lg bg-surface-raised text-sm font-semibold text-tg-text active:scale-95"
          >
            +15
          </button>

          <button
            type="button"
            onClick={() => {
              haptic.impact('light');
              timer.skip();
            }}
            className="h-9 rounded-lg bg-accent px-3 text-sm font-semibold text-white active:scale-95"
          >
            {finished ? 'OK' : "O'tkazish"}
          </button>
        </div>
      </div>
    </div>
  );
}
