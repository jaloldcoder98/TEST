import { haptic } from '../lib/telegram';
import { ChartIcon, DumbbellIcon, HistoryIcon } from './icons';

export type Tab = 'workout' | 'history' | 'stats';

const TABS: { id: Tab; label: string; Icon: typeof DumbbellIcon }[] = [
  { id: 'workout', label: 'Mashg’ulot', Icon: DumbbellIcon },
  { id: 'history', label: 'Tarix', Icon: HistoryIcon },
  { id: 'stats', label: 'Statistika', Icon: ChartIcon },
];

interface BottomNavProps {
  active: Tab;
  onChange: (tab: Tab) => void;
  /** Pulses the workout tab while a session is live. */
  workoutActive: boolean;
}

export function BottomNav({ active, onChange, workoutActive }: BottomNavProps) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 flex border-t border-surface-line bg-tg-secondary
                 pb-[env(safe-area-inset-bottom,0px)]"
    >
      {TABS.map(({ id, label, Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              haptic.selection();
              onChange(id);
            }}
            aria-current={isActive ? 'page' : undefined}
            className={`relative flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium
                        transition-colors ${isActive ? 'text-accent' : 'text-tg-hint'}`}
          >
            <Icon width={20} height={20} />
            {label}
            {id === 'workout' && workoutActive && (
              <span className="absolute right-[26%] top-2 h-1.5 w-1.5 rounded-full bg-success" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
