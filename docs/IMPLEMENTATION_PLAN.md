# GYM Platform — Implementation Plan

Phases follow spec §60/§63. Each phase ends with tests + lint + type-check green and docs
updated before moving on (spec §63). This plan does not assume the whole system ships in one
sitting — realistically this is weeks of engineering, so it is broken into milestones that each
produce something runnable and reviewable.

## Phase 1 — Analysis (this delivery)
- [x] Clone and inspect `ExerciseGymGifsDB` (see `ARCHITECTURE.md` §1).
- [x] `ARCHITECTURE.md`, `DATABASE.md`, `API.md`, this file.
- [ ] Product-owner sign-off on the 3 open decisions in `ARCHITECTURE.md` §7 (push target,
      OpenAI key, media licensing) before Phase 2 starts.

## Phase 2 — Monorepo + Docker
```
gym-platform/
├── backend/app/{api,core,models,schemas,services,repositories,workers,ai}/, migrations/, tests/
├── frontend/{app,components,lib,hooks,stores,messages/{en,ru,uz}.json}/
├── bot/{handlers,keyboards,middlewares,services,locales}/
├── data/exercises/          # imported snapshot from ExerciseGymGifsDB, not the GIFs themselves
├── scripts/{import_exercises.py, seed_database.py}
├── docker-compose.yml, .env.example, README.md, Makefile
```
Deliverable: `docker compose up` boots empty Postgres/Redis/backend/frontend/bot containers that
all report healthy, with no business logic yet.

## Phase 3 — Database
- SQLAlchemy models for every table in `DATABASE.md`.
- Alembic baseline migration.
- `scripts/import_exercises.py`: reads the cloned `ExerciseGymGifsDB` `api/en/exercises.json`,
  upserts `muscles/equipment/body_parts/categories` lookups, then `exercises` +
  `exercise_translations` (language=`en`). `ru`/`uz` rows are left empty by design (see
  `ARCHITECTURE.md` §5) — the importer must not fabricate them.
- Decide & implement the `secondary_muscles` representation (array vs. join table — flagged in
  `DATABASE.md`).
- Deliverable: `alembic upgrade head && python scripts/import_exercises.py` leaves 1323 exercises
  queryable in Postgres.

## Phase 4 — Backend API
Build against `API.md`, in this order (each depends on the last): auth → users → exercises
(read-only, pagination + pg_trgm search) → workouts/workout-sessions/sets → nutrition (manual
logging first, AI analysis stubbed) → progress → admin. JWT + refresh tokens, rate limiting,
CORS, per-user authorization enforced in the repository layer. Deliverable: every endpoint in
`API.md` except `/ai/*` responds correctly against a seeded DB, with pytest coverage on auth,
exercise search/filter, workout logging, and authorization boundaries (user A cannot read user
B's data).

## Phase 5 — Frontend
Design system first (Button/Card/Modal/... from spec §54) in dark mode, then: auth pages →
dashboard → exercise browse/detail/search/filter → workout create/session/tracking → progress
charts. next-intl wired from day one (no hardcoded strings, even in Phase 5 scaffolding).
Deliverable: a user can register, browse exercises, build and log a workout, and see it reflected
in the dashboard, entirely through the UI, in all 3 languages.

## Phase 6 — Telegram bot
aiogram 3.x, calling the same FastAPI backend — no duplicated business logic. Onboarding
(`/start` → language → profile) → main menu → workout tracking with inline-keyboard set
completion → nutrition logging. Deliverable: a Telegram user and a web user can be the same
account, and workouts/nutrition logged on either surface show up on both.

## Phase 7 — AI
`AIProvider` abstraction + `OpenAIProvider`, prompt files, Pydantic-validated structured output.
AI Coach chat → workout generator (DB-grounded, spec §51) → exercise replacement (spec §52) →
food image analysis pipeline (spec §50) → nutrition assistant backed by `food_items`.
**Requires an OpenAI API key to test end-to-end** — the abstraction itself does not.
Deliverable: `/ai/*` endpoints pass schema validation against real model output, and refuse to
emit an exercise_id or food item that doesn't exist in the DB.

## Phase 8 — Tests
Backend: pytest (unit + integration, including the AI schema-validation and food-analysis
pipeline). Frontend: Vitest (components/hooks) + Playwright (register → workout → log food
happy path). Bot: handler unit tests with aiogram's test utilities. Deliverable: CI-runnable
suite, all green.

## Phase 9 — Security/performance audit
Walk spec §37 and §40 as a checklist against the actual implementation: JWT/refresh correctness,
rate limits actually enforced, file-upload validation (MIME/size/dimensions), SQL injection
surface (should be zero given the ORM, but verify raw-SQL usage), cross-user data access attempts
in tests, Redis cache never keyed by anything user-private, exercise list pagination enforced.

## Phase 10 — Production documentation
README with real setup steps (verified by actually running them), finalized `.env.example`,
confirm `git log`/`git diff` contain no committed secrets, `docs/ARCHITECTURE.md` updated for
any decisions that changed during implementation.

## Sequencing note
Phases 2–4 (backend + DB) can start immediately once the open decisions in `ARCHITECTURE.md` §7
are answered. Phase 5 (frontend) and Phase 6 (bot) can run in parallel once Phase 4's API is
stable, since both are pure clients of it. Phase 7 (AI) only needs Phase 4's exercise/nutrition
endpoints, so it can also start before Phase 5/6 finish, if the OpenAI key is available earlier.
