import type { Request, Response } from 'express';
import { z } from 'zod';
import { requireUser } from '../../middleware/telegram-auth.js';
import * as workoutService from './workout.service.js';
import type { CreateWorkoutInput, ListWorkoutsQuery } from './workout.schema.js';

const idParam = z.object({ id: z.string().uuid() });

/** POST /api/workouts */
export async function create(req: Request, res: Response): Promise<void> {
  const user = requireUser(req);
  const result = await workoutService.createWorkout(user.id, req.body as CreateWorkoutInput);
  res.status(201).json(result);
}

/** GET /api/workouts */
export async function list(req: Request, res: Response): Promise<void> {
  const user = requireUser(req);
  const query = res.locals.query as ListWorkoutsQuery;
  res.json(await workoutService.listWorkouts(user.id, query));
}

/** GET /api/workouts/:id */
export async function getById(req: Request, res: Response): Promise<void> {
  const user = requireUser(req);
  const { id } = idParam.parse(req.params);
  res.json({ workout: await workoutService.getWorkout(user.id, id) });
}

/** DELETE /api/workouts/:id */
export async function remove(req: Request, res: Response): Promise<void> {
  const user = requireUser(req);
  const { id } = idParam.parse(req.params);
  await workoutService.deleteWorkout(user.id, id);
  res.status(204).send();
}
