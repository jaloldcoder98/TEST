import { createHmac, timingSafeEqual } from 'node:crypto';

export interface TelegramUser {
  id: bigint;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

export interface ParsedInitData {
  user: TelegramUser;
  authDate: Date;
  queryId?: string;
  startParam?: string;
  chatType?: string;
  raw: URLSearchParams;
}

export type InitDataFailure =
  | 'EMPTY'
  | 'MISSING_HASH'
  | 'BAD_SIGNATURE'
  | 'EXPIRED'
  | 'MISSING_AUTH_DATE'
  | 'MISSING_USER'
  | 'MALFORMED_USER';

export class InitDataError extends Error {
  constructor(readonly reason: InitDataFailure, message: string) {
    super(message);
    this.name = 'InitDataError';
  }
}

/**
 * Derive the signing key Telegram uses for Mini App initData:
 *
 *   secret_key = HMAC_SHA256(key = "WebAppData", message = bot_token)
 *
 * Note the arguments are the reverse of the Login Widget scheme, where the
 * secret is SHA256(bot_token). Getting this backwards is the usual reason
 * verification "mysteriously" always fails.
 */
const deriveSecretKey = (botToken: string): Buffer =>
  createHmac('sha256', 'WebAppData').update(botToken).digest();

/**
 * Build the data-check-string: every field except `hash` (and `signature`,
 * which belongs to the Ed25519 third-party scheme), sorted by key,
 * joined as `key=value` with newlines.
 */
const buildDataCheckString = (params: URLSearchParams): string =>
  [...params.entries()]
    .filter(([key]) => key !== 'hash' && key !== 'signature')
    .map(([key, value]) => `${key}=${value}`)
    .sort()
    .join('\n');

const hexEquals = (a: string, b: string): boolean => {
  if (a.length !== b.length) return false;
  try {
    return timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
  } catch {
    return false;
  }
};

/**
 * Verify and parse the `initData` string handed to the Mini App by Telegram.
 *
 * @param initData  Raw query-string as received from `WebApp.initData`.
 * @param botToken  Bot token from @BotFather.
 * @param maxAgeSec Reject initData older than this (replay protection).
 * @throws {InitDataError} when the payload is absent, forged, or stale.
 */
export function verifyTelegramInitData(
  initData: string,
  botToken: string,
  maxAgeSec: number,
): ParsedInitData {
  if (!initData) {
    throw new InitDataError('EMPTY', 'initData is empty');
  }

  const params = new URLSearchParams(initData);

  const hash = params.get('hash');
  if (!hash) {
    throw new InitDataError('MISSING_HASH', 'initData has no hash field');
  }

  const expected = createHmac('sha256', deriveSecretKey(botToken))
    .update(buildDataCheckString(params))
    .digest('hex');

  if (!hexEquals(hash, expected)) {
    throw new InitDataError('BAD_SIGNATURE', 'initData signature does not match');
  }

  const authDateRaw = params.get('auth_date');
  if (!authDateRaw) {
    throw new InitDataError('MISSING_AUTH_DATE', 'initData has no auth_date');
  }

  const authDateSec = Number(authDateRaw);
  if (!Number.isFinite(authDateSec)) {
    throw new InitDataError('MISSING_AUTH_DATE', 'initData auth_date is not a number');
  }

  const ageSec = Math.floor(Date.now() / 1000) - authDateSec;
  if (ageSec > maxAgeSec) {
    throw new InitDataError('EXPIRED', `initData is ${ageSec}s old (max ${maxAgeSec}s)`);
  }

  const userRaw = params.get('user');
  if (!userRaw) {
    // Happens when the Mini App is opened from an inline button without user
    // context; we cannot identify anyone, so treat it as unauthenticated.
    throw new InitDataError('MISSING_USER', 'initData has no user field');
  }

  let parsedUser: Record<string, unknown>;
  try {
    parsedUser = JSON.parse(userRaw) as Record<string, unknown>;
  } catch {
    throw new InitDataError('MALFORMED_USER', 'initData user field is not valid JSON');
  }

  if (typeof parsedUser.id !== 'number' && typeof parsedUser.id !== 'string') {
    throw new InitDataError('MALFORMED_USER', 'initData user.id is missing');
  }

  const user: TelegramUser = {
    id: BigInt(parsedUser.id as number | string),
    first_name: typeof parsedUser.first_name === 'string' ? parsedUser.first_name : undefined,
    last_name: typeof parsedUser.last_name === 'string' ? parsedUser.last_name : undefined,
    username: typeof parsedUser.username === 'string' ? parsedUser.username : undefined,
    language_code: typeof parsedUser.language_code === 'string' ? parsedUser.language_code : undefined,
    is_premium: parsedUser.is_premium === true,
    photo_url: typeof parsedUser.photo_url === 'string' ? parsedUser.photo_url : undefined,
  };

  return {
    user,
    authDate: new Date(authDateSec * 1000),
    queryId: params.get('query_id') ?? undefined,
    startParam: params.get('start_param') ?? undefined,
    chatType: params.get('chat_type') ?? undefined,
    raw: params,
  };
}
