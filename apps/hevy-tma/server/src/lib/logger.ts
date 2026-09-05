import pino from 'pino';
import { env, isProduction } from '../config/env.js';

export const logger = pino({
  level: env.LOG_LEVEL,
  transport: isProduction ? undefined : { target: 'pino-pretty', options: { colorize: true } },
  redact: {
    // initData carries a signature and the user's Telegram profile — never log it.
    paths: ['req.headers.authorization', 'req.headers["x-telegram-init-data"]'],
    remove: true,
  },
});
