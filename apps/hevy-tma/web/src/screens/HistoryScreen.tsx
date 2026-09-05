import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { formatDuration, formatVolume } from '../lib/format';
import { HistoryIcon } from '../components/icons';

export function HistoryScreen() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['workouts'],
    queryFn: () => api.listWorkouts(20),
  });

  if (isPending) return <Centered>Yuklanmoqda…</Centered>;
  if (isError) return <Centered>Tarixni yuklab bo'lmadi.</Centered>;

  if (data.items.length === 0) {
    return (
      <Centered>
        <HistoryIcon width={32} height={32} className="mb-3 text-tg-hint" />
        Hali mashg'ulot yo'q. Birinchisini boshlang!
      </Centered>
    );
  }

  return (
    <div className="space-y-3 px-3 py-3">
      {data.items.map((workout) => (
        <article key={workout.id} className="card space-y-2">
          <header>
            <h3 className="font-semibold">{workout.title}</h3>
            <p className="text-xs text-tg-hint">
              {new Date(workout.startedAt).toLocaleString('uz-UZ', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </header>

          <div className="flex gap-4 text-xs text-tg-hint">
            <span>⏱ {formatDuration(workout.durationSec ?? 0)}</span>
            <span>🏋 {formatVolume(workout.totalVolumeKg)}</span>
            <span>✅ {workout.totalSets} set</span>
          </div>

          <ul className="space-y-1 border-t border-surface-line pt-2 text-sm">
            {workout.exercises.map((item) => (
              <li key={item.id} className="flex justify-between gap-3">
                <span className="truncate">{item.exercise.name}</span>
                <span className="shrink-0 tabular-nums text-tg-hint">{item.sets.length} set</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-8 text-center text-sm text-tg-hint">
      {children}
    </div>
  );
}
