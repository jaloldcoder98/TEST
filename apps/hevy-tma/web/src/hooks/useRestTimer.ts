import { useEffect, useRef, useState } from 'react';
import { haptic } from '../lib/telegram';
import { useWorkoutStore } from '../store/workout-store';

export interface RestTimer {
  active: boolean;
  remainingSec: number;
  durationSec: number;
  /** 0..1, for the progress ring. */
  progress: number;
  start: (seconds: number) => void;
  add: (seconds: number) => void;
  skip: () => void;
}

/**
 * Countdown driven by the absolute `endsAt` timestamp in the store, so the
 * timer stays correct across re-renders, reloads, and WebView suspension.
 * Fires a haptic notification once when it reaches zero.
 */
export function useRestTimer(): RestTimer {
  const restTimer = useWorkoutStore((state) => state.restTimer);
  const startRest = useWorkoutStore((state) => state.startRest);
  const adjustRest = useWorkoutStore((state) => state.adjustRest);
  const stopRest = useWorkoutStore((state) => state.stopRest);

  const [remainingSec, setRemainingSec] = useState(0);
  const firedRef = useRef(false);

  useEffect(() => {
    if (!restTimer) {
      setRemainingSec(0);
      firedRef.current = false;
      return;
    }

    firedRef.current = false;

    const tick = (): void => {
      const remaining = Math.max(0, Math.ceil((restTimer.endsAt - Date.now()) / 1000));
      setRemainingSec(remaining);

      if (remaining === 0 && !firedRef.current) {
        firedRef.current = true;
        haptic.success();
      }
    };

    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [restTimer]);

  const durationSec = restTimer?.durationSec ?? 0;

  return {
    active: restTimer !== null,
    remainingSec,
    durationSec,
    progress: durationSec > 0 ? 1 - remainingSec / durationSec : 0,
    start: startRest,
    add: adjustRest,
    skip: stopRest,
  };
}
