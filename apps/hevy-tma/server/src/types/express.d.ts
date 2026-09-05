import type { User } from '@prisma/client';
import type { ParsedInitData } from '../lib/telegram-init-data.js';

declare global {
  namespace Express {
    interface Request {
      /** Set by `telegramAuth` — the authenticated app user. */
      user?: User;
      /** Set by `telegramAuth` — the verified Telegram payload. */
      initData?: ParsedInitData;
    }
  }
}

export {};
