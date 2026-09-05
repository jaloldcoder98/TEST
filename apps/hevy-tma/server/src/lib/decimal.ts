import { Prisma } from '@prisma/client';

/** Prisma Decimal -> number, preserving null/undefined. */
export function toNumber(value: Prisma.Decimal | null | undefined): number | null {
  return value == null ? null : value.toNumber();
}

/** number -> Prisma Decimal, preserving null/undefined. */
export function toDecimal(value: number | null | undefined): Prisma.Decimal | null {
  return value == null ? null : new Prisma.Decimal(value);
}

/**
 * Epley one-rep-max estimate: 1RM = w x (1 + reps/30).
 * Returns the weight itself for a single rep, and null when it makes no sense.
 */
export function estimateOneRepMax(weightKg: number | null, reps: number | null): number | null {
  if (weightKg == null || reps == null || weightKg <= 0 || reps <= 0) return null;
  if (reps === 1) return weightKg;
  // Above ~12 reps the formula drifts badly; cap the input rather than lie.
  const effectiveReps = Math.min(reps, 12);
  return Number((weightKg * (1 + effectiveReps / 30)).toFixed(2));
}
