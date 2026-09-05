import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BottomNav, type Tab } from './components/BottomNav';
import { WorkoutTracker } from './components/WorkoutTracker';
import { HistoryScreen } from './screens/HistoryScreen';
import { StatsScreen } from './screens/StatsScreen';
import { ApiError, api } from './lib/api';
import { initTelegram, isTelegramClient } from './lib/telegram';
import { useWorkoutStore } from './store/workout-store';

export default function App() {
  const [tab, setTab] = useState<Tab>('workout');
  const workoutActive = useWorkoutStore((state) => state.startedAt !== null);

  // Expand the viewport and apply Telegram's theme before the first paint of
  // real content — the SDK is safe to call more than once.
  useEffect(() => {
    initTelegram();
  }, []);

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: () => api.me(),
    retry: (failureCount, error) =>
      // A rejected signature will never succeed on retry.
      !(error instanceof ApiError && error.status === 401) && failureCount < 2,
    staleTime: 10 * 60 * 1000,
  });

  if (meQuery.isPending) {
    return (
      <Screen>
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        <p className="mt-4 text-sm text-tg-hint">Yuklanmoqda…</p>
      </Screen>
    );
  }

  if (meQuery.isError) {
    const unauthorized = meQuery.error instanceof ApiError && meQuery.error.status === 401;
    return (
      <Screen>
        <h2 className="text-lg font-bold">
          {unauthorized ? 'Autentifikatsiya muvaffaqiyatsiz' : 'Serverga ulanib bo‘lmadi'}
        </h2>
        <p className="mt-2 max-w-xs text-sm text-tg-hint">
          {unauthorized && !isTelegramClient()
            ? 'Bu ilovani Telegram orqali oching — u Telegram imzosi bilan ishlaydi.'
            : meQuery.error instanceof ApiError
              ? meQuery.error.message
              : String(meQuery.error)}
        </p>
        <button
          type="button"
          onClick={() => void meQuery.refetch()}
          className="mt-6 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white active:scale-95"
        >
          Qayta urinish
        </button>
      </Screen>
    );
  }

  const user = meQuery.data.user;

  return (
    <div className="min-h-full pb-[calc(3.75rem+env(safe-area-inset-bottom,0px))]">
      {tab === 'workout' && <WorkoutTracker user={user} />}
      {tab === 'history' && <HistoryScreen />}
      {tab === 'stats' && <StatsScreen />}

      <BottomNav active={tab} onChange={setTab} workoutActive={workoutActive} />
    </div>
  );
}

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-8 text-center">
      {children}
    </div>
  );
}
