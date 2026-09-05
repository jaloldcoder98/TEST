import type { NextFunction, Request, Response } from 'express';
import { env } from '../config/env.js';
import { HttpError } from '../lib/http-error.js';
import { logger } from '../lib/logger.js';
import { prisma } from '../lib/prisma.js';
import {
  InitDataError,
  verifyTelegramInitData,
  type ParsedInitData,
} from '../lib/telegram-init-data.js';

const INIT_DATA_HEADER = 'x-telegram-init-data';

/**
 * Read initData from either `X-Telegram-Init-Data` or
 * `Authorization: tma <initData>` (the convention @telegram-apps uses).
 */
function readInitData(req: Request): string | undefined {
  const header = req.get(INIT_DATA_HEADER);
  if (header) return header;

  const authorization = req.get('authorization');
  if (authorization) {
    const [scheme, ...rest] = authorization.split(' ');
    if (scheme?.toLowerCase() === 'tma' && rest.length > 0) return rest.join(' ');
  }

  return undefined;
}

/** Development-only stand-in so the API is usable outside the Telegram client. */
function devInitData(): ParsedInitData {
  return {
    user: { id: env.DEV_TELEGRAM_ID, first_name: 'Dev', username: 'dev_user', language_code: 'uz' },
    authDate: new Date(),
    raw: new URLSearchParams(),
  };
}

/**
 * Verifies the Telegram Mini App signature and upserts the corresponding user.
 * On success `req.user` and `req.initData` are populated.
 */
export async function telegramAuth(
  req: Request,
  _res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const rawInitData = readInitData(req);
    let parsed: ParsedInitData;

    if (rawInitData) {
      parsed = verifyTelegramInitData(
        rawInitData,
        // env.ts guarantees a token exists unless the dev bypass is on.
        env.TELEGRAM_BOT_TOKEN as string,
        env.TELEGRAM_INITDATA_MAX_AGE_SEC,
      );
    } else if (env.AUTH_DEV_BYPASS) {
      logger.warn('AUTH_DEV_BYPASS is on — authenticating without a Telegram signature');
      parsed = devInitData();
    } else {
      throw HttpError.unauthorized('Missing Telegram initData');
    }

    const tg = parsed.user;

    // Upsert on every request: it keeps the profile fresh and removes the need
    // for a separate registration step. Telegram is the source of truth here.
    const user = await prisma.user.upsert({
      where: { telegramId: tg.id },
      create: {
        telegramId: tg.id,
        username: tg.username ?? null,
        firstName: tg.first_name ?? null,
        lastName: tg.last_name ?? null,
        languageCode: tg.language_code ?? null,
        photoUrl: tg.photo_url ?? null,
        isPremium: tg.is_premium ?? false,
      },
      update: {
        username: tg.username ?? null,
        firstName: tg.first_name ?? null,
        lastName: tg.last_name ?? null,
        languageCode: tg.language_code ?? null,
        photoUrl: tg.photo_url ?? null,
        isPremium: tg.is_premium ?? false,
        lastSeenAt: new Date(),
      },
    });

    req.user = user;
    req.initData = parsed;
    next();
  } catch (error) {
    if (error instanceof InitDataError) {
      // Log the machine-readable reason, return a generic message to the client.
      logger.warn({ reason: error.reason }, 'initData rejected');
      next(HttpError.unauthorized('Invalid Telegram initData'));
      return;
    }
    next(error);
  }
}

/** Narrowing helper for controllers running behind `telegramAuth`. */
export function requireUser(req: Request): NonNullable<Request['user']> {
  if (!req.user) throw HttpError.unauthorized();
  return req.user;
}
