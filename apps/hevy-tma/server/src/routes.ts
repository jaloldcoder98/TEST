import { Router, type Request, type Response } from 'express';
import { exerciseRouter } from './modules/exercises/exercise.routes.js';
import { statsRouter } from './modules/stats/stats.routes.js';
import { workoutRouter } from './modules/workouts/workout.routes.js';
import { telegramAuth } from './middleware/telegram-auth.js';
import { requireUser } from './middleware/telegram-auth.js';
import { asyncHandler } from './middleware/async-handler.js';

export const apiRouter: Router = Router();

// Everything below this line requires a verified Telegram initData signature.
apiRouter.use(telegramAuth);

/** GET /api/me — the authenticated profile, used by the app on boot. */
apiRouter.get(
  '/me',
  asyncHandler(async (req: Request, res: Response) => {
    const user = requireUser(req);
    res.json({
      user: {
        id: user.id,
        telegramId: user.telegramId.toString(),
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        photoUrl: user.photoUrl,
        languageCode: user.languageCode,
        unit: user.unit,
        defaultRestSeconds: user.defaultRestSeconds,
      },
    });
  }),
);

apiRouter.use('/exercises', exerciseRouter);
apiRouter.use('/workouts', workoutRouter);
apiRouter.use('/stats', statsRouter);
