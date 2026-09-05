import { z } from 'zod';

const csv = z
  .string()
  .transform((value) => value.split(',').map((part) => part.trim()).filter(Boolean));

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(4000),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace']).default('info'),

  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),

  TELEGRAM_BOT_TOKEN: z.string().min(1).optional(),
  TELEGRAM_INITDATA_MAX_AGE_SEC: z.coerce.number().int().positive().default(86_400),
  AUTH_DEV_BYPASS: z
    .enum(['true', 'false'])
    .default('false')
    .transform((value) => value === 'true'),
  DEV_TELEGRAM_ID: z.coerce.bigint().default(100_000_001n),

  CORS_ORIGINS: csv.default('http://localhost:5173'),
});

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  const issues = parsed.error.issues.map((i) => `  - ${i.path.join('.')}: ${i.message}`).join('\n');
  throw new Error(`Invalid environment configuration:\n${issues}`);
}

export const env = parsed.data;

// A dev bypass in production would let anyone impersonate any user — refuse to boot.
if (env.AUTH_DEV_BYPASS && env.NODE_ENV === 'production') {
  throw new Error('AUTH_DEV_BYPASS must not be enabled when NODE_ENV=production');
}

if (!env.TELEGRAM_BOT_TOKEN && !env.AUTH_DEV_BYPASS) {
  throw new Error('TELEGRAM_BOT_TOKEN is required unless AUTH_DEV_BYPASS=true');
}

export const isProduction = env.NODE_ENV === 'production';
