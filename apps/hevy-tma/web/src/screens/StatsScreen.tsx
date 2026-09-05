import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { formatDuration, formatVolume, PR_LABELS } from '../lib/format';
import { TrophyIcon } from '../components/icons';

export function StatsScreen() {
  const summary = useQuery({ queryKey: ['stats', 'summary'], queryFn: () => api.statsSummary() });
  const records = useQuery({ queryKey: ['stats', 'prs'], queryFn: () => api.personalRecords() });

  if (summary.isPending) {
    return <p className="py-16 text-center text-sm text-tg-hint">Yuklanmoqda…</p>;
  }
  if (summary.isError) {
    return <p className="py-16 text-center text-sm text-tg-destructive">Statistikani yuklab bo'lmadi.</p>;
  }

  const { totals, weeklyVolume } = summary.data;
  const peak = Math.max(1, ...weeklyVolume.map((week) => week.volumeKg));

  return (
    <div className="space-y-4 px-3 py-3">
      <div className="grid grid-cols-2 gap-2">
        <Tile label="Mashg'ulotlar" value={String(totals.workouts)} />
        <Tile label="Umumiy hajm" value={formatVolume(totals.volumeKg)} />
        <Tile label="Setlar" value={String(totals.sets)} />
        <Tile label="Umumiy vaqt" value={formatDuration(totals.durationSec)} />
      </div>

      <section className="card">
        <h3 className="mb-3 text-sm font-semibold">Haftalik hajm</h3>
        <div className="flex h-32 items-end gap-1">
          {weeklyVolume.map((week) => (
            <div key={week.weekStart} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-t bg-accent/70 transition-all"
                style={{ height: `${Math.max(2, (week.volumeKg / peak) * 100)}%` }}
                title={`${week.weekStart}: ${formatVolume(week.volumeKg)}`}
              />
            </div>
          ))}
        </div>
        <p className="mt-2 text-center text-[11px] text-tg-hint">
          Eng yuqori hafta: {formatVolume(peak)}
        </p>
      </section>

      <section className="card">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <TrophyIcon width={16} height={16} className="text-amber-400" />
          Shaxsiy rekordlar ({totals.personalRecords})
        </h3>

        {records.data?.items.length === 0 && (
          <p className="py-4 text-center text-sm text-tg-hint">
            Hali rekord yo'q — birinchi mashg'ulotingizni yakunlang.
          </p>
        )}

        <ul className="space-y-2">
          {records.data?.items.slice(0, 20).map((record) => (
            <li key={record.id} className="flex items-center justify-between gap-3 text-sm">
              <div className="min-w-0">
                <div className="truncate font-medium">{record.exercise.name}</div>
                <div className="text-xs text-tg-hint">{PR_LABELS[record.type]}</div>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-bold tabular-nums text-success">
                  {record.value}
                  {record.type === 'MAX_REPS' ? '' : ' kg'}
                </div>
                {record.weightKg != null && record.reps != null && (
                  <div className="text-[11px] tabular-nums text-tg-hint">
                    {record.weightKg} × {record.reps}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="card py-3">
      <div className="text-[11px] uppercase tracking-wide text-tg-hint">{label}</div>
      <div className="mt-0.5 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
