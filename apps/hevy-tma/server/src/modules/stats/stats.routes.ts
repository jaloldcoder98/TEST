import { WorkoutStatus } from '@prisma/client';
import { Router, type Request, type Response } from 'express';
import { z } from 'zod';
import { prisma } from '../../lib/prisma.js';
import { asyncHandler } from '../../middleware/async-handler.js';
import { requireUser } from '../../middleware/telegram-auth.js';
import { validateQuery } from '../../middleware/validate.js';

export const statsRouter: Router = Router();

const summaryQuerySchema = z.object({
  /** Size of the trailing window used for the volume chart. */
  weeks: z.coerce.number().int().min(1).max(52).default(12),
});

const startOfWeek = (date: Date): Date => {
  const result = new Date(date);
  result.setUTCHours(0, 0, 0, 0);
  // ISO weeks start on Monday.
  const dayOffset = (result.getUTCDay() + 6) % 7;
  result.setUTCDate(result.getUTCDate() - dayOffset);
  return result;
};

/** GET /api/stats/summary — headline numbers plus a weekly volume series. */
statsRouter.get(
  '/summary',
  validateQuery(summaryQuerySchema),
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    const { weeks } = res.locals.query as z.infer<typeof summaryQuerySchema>;

    const since = startOfWeek(new Date());
    since.setUTCDate(since.getUTCDate() - (weeks - 1) * 7);

    const [totals, recent, prCount] = await Promise.all([
      prisma.workout.aggregate({
        where: { userId: user.id, status: WorkoutStatus.COMPLETED },
        _count: { _all: true },
        _sum: { totalVolumeKg: true, totalSets: true, totalReps: true, durationSec: true },
      }),
      prisma.workout.findMany({
        where: { userId: user.id, status: WorkoutStatus.COMPLETED, startedAt: { gte: since } },
        select: { startedAt: true, totalVolumeKg: true },
        orderBy: { startedAt: 'asc' },
      }),
      prisma.personalRecord.count({ where: { userId: user.id } }),
    ]);

    // Pre-seed every bucket so weeks with no training render as zero, not a gap.
    const buckets = new Map<string, { weekStart: string; volumeKg: number; workouts: number }>();
    for (let index = 0; index < weeks; index += 1) {
      const weekStart = new Date(since);
      weekStart.setUTCDate(weekStart.getUTCDate() + index * 7);
      const key = weekStart.toISOString().slice(0, 10);
      buckets.set(key, { weekStart: key, volumeKg: 0, workouts: 0 });
    }

    for (const workout of recent) {
      const key = startOfWeek(workout.startedAt).toISOString().slice(0, 10);
      const bucket = buckets.get(key);
      if (!bucket) continue;
      bucket.volumeKg += workout.totalVolumeKg.toNumber();
      bucket.workouts += 1;
    }

    res.json({
      totals: {
        workouts: totals._count._all,
        volumeKg: totals._sum.totalVolumeKg?.toNumber() ?? 0,
        sets: totals._sum.totalSets ?? 0,
        reps: totals._sum.totalReps ?? 0,
        durationSec: totals._sum.durationSec ?? 0,
        personalRecords: prCount,
      },
      weeklyVolume: [...buckets.values()].map((bucket) => ({
        ...bucket,
        volumeKg: Number(bucket.volumeKg.toFixed(2)),
      })),
    });
  }),
);

/** GET /api/stats/personal-records — every current best, newest first. */
statsRouter.get(
  '/personal-records',
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);

    const records = await prisma.personalRecord.findMany({
      where: { userId: user.id },
      orderBy: { achievedAt: 'desc' },
      include: { exercise: { select: { id: true, name: true, muscleGroup: true, thumbUrl: true } } },
    });

    res.json({
      items: records.map((record) => ({
        id: record.id,
        type: record.type,
        value: record.value.toNumber(),
        weightKg: record.weightKg?.toNumber() ?? null,
        reps: record.reps,
        achievedAt: record.achievedAt,
        exercise: record.exercise,
      })),
    });
  }),
);
