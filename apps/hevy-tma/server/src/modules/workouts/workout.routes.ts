import { Router } from 'express';
import { asyncHandler } from '../../middleware/async-handler.js';
import { validateBody, validateQuery } from '../../middleware/validate.js';
import * as controller from './workout.controller.js';
import { createWorkoutSchema, listWorkoutsQuerySchema } from './workout.schema.js';

export const workoutRouter: Router = Router();

workoutRouter.post('/', validateBody(createWorkoutSchema), asyncHandler(controller.create));
workoutRouter.get('/', validateQuery(listWorkoutsQuerySchema), asyncHandler(controller.list));
workoutRouter.get('/:id', asyncHandler(controller.getById));
workoutRouter.delete('/:id', asyncHandler(controller.remove));
