import { Equipment, MuscleGroup, type Prisma } from '@prisma/client';
import { Router, type Request, type Response } from 'express';
import { z } from 'zod';
import { HttpError } from '../../lib/http-error.js';
import { prisma } from '../../lib/prisma.js';
import { asyncHandler } from '../../middleware/async-handler.js';
import { requireUser } from '../../middleware/telegram-auth.js';
import { validateBody, validateQuery } from '../../middleware/validate.js';

const listQuerySchema = z.object({
  q: z.string().trim().min(1).max(80).optional(),
  muscleGroup: z.nativeEnum(MuscleGroup).optional(),
  equipment: z.nativeEnum(Equipment).optional(),
  limit: z.coerce.number().int().min(1).max(100).default(50),
  cursor: z.string().uuid().optional(),
});

const createExerciseSchema = z.object({
  name: z.string().trim().min(2).max(120),
  muscleGroup: z.nativeEnum(MuscleGroup),
  equipment: z.nativeEnum(Equipment).default(Equipment.OTHER),
  description: z.string().max(2000).nullish(),
});

const slugify = (name: string): string =>
  name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);

export const exerciseRouter: Router = Router();

/** GET /api/exercises — built-in library plus the caller's own exercises. */
exerciseRouter.get(
  '/',
  validateQuery(listQuerySchema),
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    const query = res.locals.query as z.infer<typeof listQuerySchema>;

    const where: Prisma.ExerciseWhereInput = {
      AND: [
        { OR: [{ createdById: null }, { createdById: user.id }] },
        ...(query.q ? [{ name: { contains: query.q, mode: 'insensitive' as const } }] : []),
        ...(query.muscleGroup ? [{ muscleGroup: query.muscleGroup }] : []),
        ...(query.equipment ? [{ equipment: query.equipment }] : []),
      ],
    };

    const rows = await prisma.exercise.findMany({
      where,
      orderBy: [{ name: 'asc' }, { id: 'asc' }],
      take: query.limit + 1,
      ...(query.cursor ? { cursor: { id: query.cursor }, skip: 1 } : {}),
      select: {
        id: true,
        slug: true,
        name: true,
        muscleGroup: true,
        secondaryMuscles: true,
        equipment: true,
        kind: true,
        thumbUrl: true,
        imageUrl: true,
        createdById: true,
      },
    });

    const hasMore = rows.length > query.limit;
    const items = hasMore ? rows.slice(0, query.limit) : rows;

    res.json({
      items: items.map(({ createdById, ...rest }) => ({ ...rest, isCustom: createdById !== null })),
      nextCursor: hasMore ? (items.at(-1)?.id ?? null) : null,
    });
  }),
);

/** GET /api/exercises/muscle-groups — counts for the library's filter chips. */
exerciseRouter.get(
  '/muscle-groups',
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    const grouped = await prisma.exercise.groupBy({
      by: ['muscleGroup'],
      where: { OR: [{ createdById: null }, { createdById: user.id }] },
      _count: { _all: true },
      orderBy: { muscleGroup: 'asc' },
    });

    res.json({
      items: grouped.map((row) => ({ muscleGroup: row.muscleGroup, count: row._count._all })),
    });
  }),
);

/** GET /api/exercises/:id */
exerciseRouter.get(
  '/:id',
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    const { id } = z.object({ id: z.string().uuid() }).parse(req.params);

    const exercise = await prisma.exercise.findFirst({
      where: { id, OR: [{ createdById: null }, { createdById: user.id }] },
    });
    if (!exercise) throw HttpError.notFound('Exercise not found');

    const personalRecords = await prisma.personalRecord.findMany({
      where: { userId: user.id, exerciseId: id },
      orderBy: { type: 'asc' },
    });

    res.json({
      exercise,
      personalRecords: personalRecords.map((record) => ({
        type: record.type,
        value: record.value.toNumber(),
        weightKg: record.weightKg?.toNumber() ?? null,
        reps: record.reps,
        achievedAt: record.achievedAt,
      })),
    });
  }),
);

/** POST /api/exercises — a custom exercise owned by the caller. */
exerciseRouter.post(
  '/',
  validateBody(createExerciseSchema),
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    const input = req.body as z.infer<typeof createExerciseSchema>;

    // Namespaced so a custom exercise can never collide with the built-in library.
    const slug = `u-${user.id.slice(0, 8)}-${slugify(input.name)}`;

    const exercise = await prisma.exercise.create({
      data: {
        slug,
        name: input.name,
        description: input.description ?? null,
        muscleGroup: input.muscleGroup,
        equipment: input.equipment,
        createdById: user.id,
      },
    });

    res.status(201).json({ exercise });
  }),
);
