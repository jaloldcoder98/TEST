# GYM Platform

A multilingual (UZ/RU/EN) fitness platform: a web app, a Telegram bot, an AI coach, and an AI
food-photo calorie analyzer, all sharing one FastAPI backend and one PostgreSQL database — so a
user's workouts, nutrition logs, and progress are the same whether they use the site or the bot.

Status: all ten implementation phases complete (see `docs/IMPLEMENTATION_PLAN.md`) — backend API,
frontend, Telegram bot, AI coach/food analyzer, tests across all three services, and a security
audit (`docs/SECURITY_AUDIT.md`). The one thing intentionally left unconfigured is an OpenAI API
key: without one, every AI endpoint returns a clear "not configured yet" response instead of
faking data — see **AI features** below.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2 (async), PostgreSQL, Redis, ARQ, JWT auth (access + rotating
  refresh tokens), Redis-backed rate limiting on auth endpoints
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind, next-intl, TanStack Query, Zustand
- **Bot:** aiogram 3.x, calling the same backend API as the web app — no duplicated business logic
- **AI:** OpenAI, behind a swappable provider abstraction (`backend/app/ai/`) — grounded against
  the real exercise/nutrition database rather than trusting model output directly

## Quickstart — Docker Compose (recommended)

```bash
cp .env.example .env   # fill in JWT_SECRET / JWT_REFRESH_SECRET, and optionally
                        # OPENAI_API_KEY / TELEGRAM_BOT_TOKEN — see "Environment variables" below
make up                 # docker compose up --build
make migrate             # alembic upgrade head
make seed                # imports the 1323-exercise dataset into Postgres
```

- Web app: http://localhost:3000
- API: http://localhost:8000/api/v1 (health check: `/health`)
- API docs (Swagger): http://localhost:8000/docs
- Telegram bot: starts automatically if `TELEGRAM_BOT_TOKEN` is set in `.env`; otherwise the
  `telegram-bot` container will fail to start (it requires a token) — comment it out in
  `docker-compose.yml` if you don't need the bot yet.

## Quickstart — running natively (no Docker)

This is the path actually exercised end-to-end while building this project (Postgres/Redis
installed locally rather than in containers), useful for a sandboxed environment or when you'd
rather not run Docker. Requires Python 3.11+, Node 20+, PostgreSQL 16, and Redis 7 installed
locally.

```bash
# 1. Database + cache
createuser gym --pwprompt   # or: sudo -u postgres psql -c "CREATE ROLE gym LOGIN PASSWORD 'gym'"
createdb gym -O gym
redis-server --daemonize yes

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # DATABASE_URL=postgresql+asyncpg://gym:gym@localhost:5432/gym
                            # REDIS_URL=redis://localhost:6379/0
alembic upgrade head
python scripts/import_exercises.py
python scripts/seed_database.py
uvicorn app.main:app --reload   # http://localhost:8000

# 3. Frontend (separate shell)
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev   # http://localhost:3000

# 4. Telegram bot (separate shell, optional — needs a bot token from @BotFather)
cd bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=your-token BACKEND_API_URL=http://localhost:8000/api/v1 python main.py
```

## AI features (AI Coach, workout generation, nutrition Q&A, food-photo analysis)

Everything AI-related is built and wired end-to-end — backend, web app, and bot — but the
platform ships without an OpenAI key by default. Without `OPENAI_API_KEY` set, every AI endpoint
(`/api/v1/ai/*`, `/api/v1/nutrition/analyze-image`) returns a `503 AI_NOT_CONFIGURED` error with a
clear message, and both the web app's `/ai-coach` page and the bot's AI Coach menu button show the
same honest "not connected yet" notice — nothing is faked (see `docs/SECURITY_AUDIT.md` and the
AI service's own docstring in `backend/app/services/ai_service.py` for why). To turn it on, set
`OPENAI_API_KEY` (and optionally `AI_MODEL`, default `gpt-4o-mini`) in `.env` and restart the
backend — no other changes needed.

## Environment variables

See `.env.example` for the full list with safe local defaults. Never commit a filled-in `.env` —
it, `.env.local`, and `.env.*.local` are all gitignored (confirmed via `git ls-files` that none
are tracked). The variables that matter most:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string |
| `REDIS_URL` | yes | Used for the ARQ worker and auth rate limiting |
| `JWT_SECRET` / `JWT_REFRESH_SECRET` | **yes in production** | Must be unique, random values — never the `change-me-in-.env` dev defaults |
| `CORS_ORIGINS` | yes | Comma-separated allowed origins for the frontend; never `*` |
| `RATE_LIMIT_ENABLED` | no | Defaults `true`; auth endpoints are rate-limited per IP |
| `OPENAI_API_KEY` | no | Enables all AI features when set — see above |
| `TELEGRAM_BOT_TOKEN` | no | Required only if you're running the bot |
| `DEBUG` | no | Defaults `true`; **set `false` in production** (turns off SQL echo logging) |

## Repository layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, scripts/, tests/
frontend/   Next.js app (App Router), design system in components/ui/, e2e/ (Playwright)
bot/        aiogram Telegram bot — a thin client of the backend API, tests/ (handler unit tests)
data/       Source exercise dataset snapshot (JSON only — GIFs stay on the CDN, see
            docs/ARCHITECTURE.md §1.6 on media licensing)
docs/       ARCHITECTURE.md, DATABASE.md, API.md, IMPLEMENTATION_PLAN.md, SECURITY_AUDIT.md
```

## Tests

```bash
make test-backend   # pytest — 50 tests (auth, users, exercises, workouts, nutrition, progress,
                     #                    Telegram linking, AI, rate limiting)
make test-frontend   # vitest — 18 tests (utils, auth store, api client, a UI component)
make test-e2e         # playwright — the full register -> workout -> nutrition -> progress journey
                       # (needs the frontend built + running against a live backend first)
make test-bot          # pytest — 40 tests (handler logic against mocked Telegram objects)
make test               # backend + frontend + bot, in sequence
```

Running natively instead of through `docker compose exec`: `cd backend && source .venv/bin/activate
&& python -m pytest tests/ -v` (same pattern for `bot/`); `cd frontend && npm test` for Vitest,
`npm run test:e2e` for Playwright (requires `npm run build && npm run start` and the backend both
already running).

## Security

See `docs/SECURITY_AUDIT.md` for the full Phase 9 walk-through: JWT/refresh token handling,
rate limiting, SQL-injection surface (none — ORM-only), cross-user data isolation, CORS, secrets
handling, and what's intentionally deferred (e.g. workout-list pagination, response caching) with
the reasoning for each.

## License note

Exercise GIFs are sourced from a third-party dataset whose own README disclaims copyright
ownership. Do not assume redistribution rights for a commercial release — see
`docs/ARCHITECTURE.md` §1.6 before shipping.
