import { useEffect, useState } from 'react';

/**
 * Seconds elapsed since `startedAt`, ticking once per second.
 * Recomputed from the timestamp rather than incremented, so a suspended
 * WebView resumes with the correct value instead of a frozen counter.
 */
export function useElapsed(startedAt: string | null): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startedAt) {
      setElapsed(0);
      return;
    }

    const start = new Date(startedAt).getTime();
    const tick = (): void => setElapsed(Math.max(0, Math.floor((Date.now() - start) / 1000)));

    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [startedAt]);

  return elapsed;
}
