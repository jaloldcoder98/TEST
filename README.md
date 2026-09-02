# GYM Platform

A multilingual (UZ/RU/EN) fitness platform: web app + Telegram bot + AI coach + AI food
calorie analyzer, sharing one FastAPI backend and one PostgreSQL database.

Status: Phase 3 in progress. See `docs/IMPLEMENTATION_PLAN.md` for the full roadmap and
`docs/ARCHITECTURE.md` for the system design and the exercise-dataset analysis.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2 (async), PostgreSQL, Redis, ARQ, JWT auth
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind, next-intl, TanStack Query
- **Bot:** aiogram 3.x, calling the same backend — no duplicated business logic
- **AI:** OpenAI, behind a swappable provider abstraction (`backend/app/ai/`)

## Quickstart (development)

```bash
cp .env.example .env   # fill in JWT_SECRET / JWT_REFRESH_SECRET / OPENAI_API_KEY / TELEGRAM_BOT_TOKEN
make up                 # docker compose up --build
make migrate             # alembic upgrade head
make seed                # imports the 1323-exercise dataset into Postgres
```

- Web app: http://localhost:3000
- API: http://localhost:8000/api/v1 (health check: `/health`)
- API docs (Swagger): http://localhost:8000/docs

## Repository layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, scripts/, tests/
frontend/   Next.js app (App Router), design system in components/ui/
bot/        aiogram Telegram bot — a thin client of the backend API
data/       Source exercise dataset snapshot (JSON only — GIFs stay on the CDN, see
            docs/ARCHITECTURE.md §1.6 on media licensing)
docs/       ARCHITECTURE.md, DATABASE.md, API.md, IMPLEMENTATION_PLAN.md
```

## Environment variables

See `.env.example`. Never commit a filled-in `.env` — it's gitignored.

## Tests

```bash
make test-backend
make test-frontend
```

## License note

Exercise GIFs are sourced from a third-party dataset whose own README disclaims copyright
ownership. Do not assume redistribution rights for a commercial release — see
`docs/ARCHITECTURE.md` §1.6 before shipping.
