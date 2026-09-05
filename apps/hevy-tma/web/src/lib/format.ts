import type { MuscleGroup, PersonalRecordType, SetType } from '../types';

export const KG_PER_LB = 0.45359237;

export const kgToLb = (kg: number): number => kg / KG_PER_LB;
export const lbToKg = (lb: number): number => lb * KG_PER_LB;

/** mm:ss, or h:mm:ss past an hour. */
export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (value: number): string => String(value).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

export function formatVolume(kg: number): string {
  if (kg >= 1000) return `${(kg / 1000).toFixed(1)} t`;
  return `${Math.round(kg)} kg`;
}

/** Label shown in the set-number column. Warm-ups and drops are lettered. */
export function setLabel(setType: SetType, workingIndex: number): string {
  switch (setType) {
    case 'WARMUP':
      return 'W';
    case 'DROP':
      return 'D';
    case 'FAILURE':
      return 'F';
    default:
      return String(workingIndex);
  }
}

export const SET_TYPE_LABELS: Record<SetType, string> = {
  WARMUP: 'Isinish',
  NORMAL: 'Oddiy',
  DROP: 'Drop set',
  FAILURE: 'Failure',
};

export const SET_TYPE_COLORS: Record<SetType, string> = {
  WARMUP: 'text-amber-400',
  NORMAL: 'text-tg-hint',
  DROP: 'text-sky-400',
  FAILURE: 'text-rose-400',
};

export const MUSCLE_LABELS: Record<MuscleGroup, string> = {
  CHEST: "Ko'krak",
  BACK: 'Orqa',
  SHOULDERS: 'Yelka',
  BICEPS: 'Bitseps',
  TRICEPS: 'Tritseps',
  FOREARMS: 'Bilak',
  ABS: 'Press',
  QUADS: 'Kvadritseps',
  HAMSTRINGS: 'Bicep femoris',
  GLUTES: 'Dumba',
  CALVES: 'Boldir',
  ABDUCTORS: 'Abduktor',
  ADDUCTORS: 'Adduktor',
  TRAPS: 'Trapetsiya',
  NECK: "Bo'yin",
  CARDIO: 'Kardio',
  FULL_BODY: "To'liq tana",
  OTHER: 'Boshqa',
};

export const PR_LABELS: Record<PersonalRecordType, string> = {
  MAX_WEIGHT: 'Eng katta og’irlik',
  MAX_REPS: 'Eng ko’p takror',
  BEST_SET_VOLUME: 'Eng yaxshi set hajmi',
  ESTIMATED_1RM: 'Taxminiy 1RM',
};

/** Epley — mirrors the server so the UI can preview a 1RM before saving. */
export function estimateOneRepMax(weightKg: number | null, reps: number | null): number | null {
  if (!weightKg || !reps || weightKg <= 0 || reps <= 0) return null;
  if (reps === 1) return weightKg;
  return Number((weightKg * (1 + Math.min(reps, 12) / 30)).toFixed(1));
}
