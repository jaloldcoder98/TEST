# GYM Platform — Architecture

> **Note (2026-09-03):** the project is pivoting to a Telegram Mini App-first architecture.
> This document still describes the current bot+web split; the gap analysis and the plan to
> close it live in [WEBAPP_FIRST_AUDIT.md](./WEBAPP_FIRST_AUDIT.md). Update this file as part
> of that work.

Status: Phase 1 (analysis). No application code has been written yet.

## 1. Source repository analysis: `ExerciseGymGifsDB`

The URL given in the spec (`jaloldcoder98/ExerciseGymGifsDB-main-test`) does not exist. The
actual repository, reachable at `https://github.com/jaloldcoder98/ExerciseGymGifsDB`, is a fork
of `JahelCuadrado/ExerciseGymGifsDB`. Findings below are from cloning and inspecting it directly.

### 1.1 What it is

A **static JSON + GIF API**, no backend: a generator script (`scripts/generate-api.js`) walks
per-muscle folders of GIFs and produces a static `api/` tree, meant to be served over the
jsDelivr CDN straight from GitHub. `app.js`/`index.html`/`styles.css` are just the repo's own
marketing landing page — not something we reuse.

### 1.2 Scale

- 1323 exercises, 19 muscle groups, 12 equipment types, 7 body parts, 4 categories.
- 1323 `.gif` files (369 MB) + 1323 `.thumb.webp` thumbnails. Repo total ≈ 422 MB.
- Two languages only: `en` and `es`. **No Uzbek or Russian.** Per spec §6/§21, we must not
  auto-generate UZ/RU translations during import — they go through a translation/enrichment
  layer (see §5 below), seeded empty and filled progressively.

### 1.3 Exercise JSON schema (as delivered)

```json
{
  "id": "biceps/barbell-curl",
  "slug": "barbell-curl",
  "name": "Barbell Curl",
  "muscle": "biceps",
  "bodyPart": "arms",
  "equipment": "barbell",
  "category": "strength",
  "secondaryMuscles": ["forearms"],
  "instructions": ["Load the bar...", "Pre-engage the biceps...", "..."],
  "file": "biceps/barbell-curl.gif",
  "gifUrl": "https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@main/biceps/barbell-curl.gif",
  "thumbUrl": "https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@main/biceps/barbell-curl.thumb.webp"
}
```

Per-language files live at `api/<lang>/exercises/<muscle>/<slug>.json`; aggregate files
(`exercises.json`, `muscles.json`, `equipment.json`, `bodyparts.json`, `categories.json`,
`search.json`) exist per language too. `id` (`<muscle>/<slug>`) is the natural external key —
maps to our `exercises.external_id`.

### 1.4 Taxonomy values found in the data

- **Muscles (19):** abductors, abs, adductors, biceps, calves, cardio, delts, forearms, glutes,
  hamstrings, lats, levator-scapulae, pectorals, quads, serratus-anterior, spine, traps,
  triceps, upper-back.
- **Equipment (12):** band, barbell, bodyweight, cable, dumbbell, ez-bar, kettlebell, lever,
  machine, other, sled, smith. (The spec's enum is missing `sled`; add it or fold it into
  `other`/`machine` — decision needed before import.)
- **Body parts (7):** arms, back, cardio, chest, core, legs, shoulders.
- **Categories (4):** strength, stretching, cardio, plyometrics.

### 1.5 Data-quality issues (from the repo's own `audit.txt`)

- **Encoding corruption in Spanish text**: names/instructions contain mojibake (e.g. `b├¡ceps`
  instead of `bíceps`, `├│` artifacts) — a UTF-8 double-encoding bug upstream. ~200 entries
  flagged as "mezclados" (mixed EN/ES) and 38 "raw English words" left inside ES names.
  **Action:** re-normalize/re-decode ES source text before using it for anything (including as
  a translation reference for RU), or treat ES as unreliable and translate from EN only.
- **No `overrides/` directory present** in this snapshot — the repo's own manual-override
  mechanism (`overrides/<muscle>/<slug>.json` for hand-fixed names/instructions) is unused here;
  everything is machine-inferred (`scripts/enrich.js` regex rules, `scripts/translate.js`
  slug-to-Spanish templater). Treat all `name`/`instructions` as auto-generated, not curated —
  useful as a first pass, not as ground truth.
- Some GIFs are the only source of truth for what the exercise looks like; there is no
  video/step-image alternative.

### 1.6 Licensing — blocking issue for production, per spec §59

The repo's own README states plainly (translated): *"This API was created by collecting images
and GIFs pulled from the Internet. I do not own the copyright on these images and cannot grant
rights to them to third parties... GIFs belong to their respective authors."*

This means: **do not assume redistribution rights for commercial use.** Concretely:

1. Build `ExerciseMediaProvider` as an interface from day one (Phase 3/4), with a first
   implementation (`JsDelivrMediaProvider`) that just proxies today's CDN URLs, so the app
   never hard-codes those URLs into UI code.
2. Store `source` (`exercisegymgifsdb`) and `source_url` per exercise in the DB so provenance is
   always traceable.
3. Before any commercial launch: either (a) get explicit permission/license from the original
   GIF authors, (b) commission or license replacement media, or (c) self-host only GIFs cleared
   for reuse. This is a legal decision for the product owner, not something to resolve in code —
   flagged here so it isn't silently shipped.
4. For development/staging, using the CDN-hosted GIFs as-is (linking, not redistributing) is the
   lowest-risk path and is what Phase 3 will do by default.

### 1.7 Reusable scripts worth studying (not copying) before Phase 3

`scripts/generate-api.js` (aggregation logic), `scripts/enrich.js` (regex-based equipment/body
part inference — useful reference if we ever need to re-infer metadata for new GIFs),
`scripts/translate.js` (slug → Spanish name templater — same idea could inform a UZ templater,
but per spec §6 we do NOT auto-generate UZ/RU during import; a human/AI-assisted enrichment step
is separate and explicit, never silent).

## 2. Target system architecture

Three independently deployable services sharing one Postgres database through one API:

```
                    ┌─────────────────┐
                    │   PostgreSQL     │◄──────────────┐
                    └────────┬─────────┘                │
                             │                            │
                    ┌────────▼─────────┐         ┌───────┴───────┐
   Next.js  ───────►│  FastAPI backend │◄───────►│  aiogram bot   │◄──── Telegram
   (web)             │  (single source  │  HTTP    │  (thin client) │
                    │   of truth)      │         └───────────────┘
                    └────────┬─────────┘
                             │
                 ┌───────────┼───────────┐
            ┌────▼───┐  ┌────▼────┐ ┌────▼────┐
            │ Redis  │  │  Celery  │ │ AI       │
            │ cache  │  │ /ARQ     │ │ provider │
            └────────┘  │ workers  │ │ (OpenAI) │
                        └──────────┘ └─────────┘
```

Both Web and Telegram are pure clients of the FastAPI backend — neither embeds business logic
(spec §61 rule 11). The bot never talks to Postgres directly.

## 3. Technology stack

Backend: Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, PostgreSQL, Redis,
ARQ (chosen over Celery — simpler, asyncio-native, one less broker abstraction; revisit only if
a task needs Celery-specific features like complex chords/canvases), JWT (access + refresh),
OAuth-ready. Frontend: Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query,
Zustand, next-intl, Recharts, Lucide. Bot: Python, aiogram 3.x. Infra: Docker Compose,
PostgreSQL, Redis, nginx (prod only).

## 4. AI architecture

```
services/ai/
  providers/        # AIProvider interface + OpenAIProvider implementation
  prompts/          # fitness_coach.txt, nutrition_coach.txt, food_analysis.txt, ...
  schemas/          # Pydantic models AI output is validated against
```

Rules carried over verbatim from spec §15/§34/§35: no route calls OpenAI directly; every AI
response is validated with Pydantic before use; workout generation retrieves candidate exercises
from the DB first and passes them as context — the model is never allowed to invent an
`exercise_id`; food analysis follows the pipeline in spec §50 (image → vision model → food ID →
portion estimate → local nutrition DB lookup → calculation → confidence check → Pydantic
validation) rather than asking the model to freely emit macros.

## 5. Translation strategy

- `exercises` holds language-neutral fields (`slug`, `muscle`, `equipment`, `body_part`,
  `category`, media, `source*`).
- `exercise_translations` (one row per exercise × language) holds `name`, `instructions`.
  Seeded from the source repo's `en` data only (verbatim) at import time. `es` data is
  available but not imported (out of scope — spec only asks for UZ/RU/EN) and, per §1.5, is
  encoding-damaged besides.
- `ru` and `uz` rows are **not** created by the importer. An admin-panel enrichment workflow
  (Phase 4 admin API + Phase 8 seed script) lets a human or a reviewed AI-assisted pass add them
  later, exercise by exercise or in bulk, always distinguishable from the EN seed by an
  `is_machine_translated` flag so editors know what still needs review.

## 6. Project structure

See `docs/IMPLEMENTATION_PLAN.md` §Phase 2 for the concrete monorepo layout (backend/frontend/
bot/data/scripts), matching spec §47.

## 7. Open decisions that block later phases

1. **GitHub push target** — is `jaloldcoder98/TEST` the real destination repo, or a placeholder?
   Need push access (a PAT with `repo` scope) before Phase 2 can commit anything.
2. **OpenAI API key** — needed to exercise Phase 7 end-to-end; Phase 2–6 can proceed without it
   (the AI provider abstraction just needs the key to be *configurable*, not present).
3. **Media licensing** (§1.6) — needs a product-owner decision before any commercial launch;
   does not block development.
4. **`sled` equipment value** — not in the spec's enum; propose adding it rather than
   discarding data.

## 8. Implementation notes & known gaps (post-build, Phase 10)

How the open decisions above actually resolved, plus decisions made and gaps left open during
Phases 4–9 that this document didn't originally anticipate:

1. **GitHub target** — confirmed as `jaloldcoder98/TEST`; a PAT was provided and used for every
   push in this build (kept out of git via `.env`/shell env only, never committed — verified with
   `git ls-files`).
2. **OpenAI API key** — still not provided as of Phase 10. Every AI feature (chat coach, workout
   generation, nutrition Q&A, food-photo analysis) is fully built and wired end-to-end across
   backend, web app, and bot, but returns an honest `503 AI_NOT_CONFIGURED` until a key is set.
   See the README's "AI features" section.
3. **`sled` equipment value** — added to the `equipment` enum/table; confirmed present in the
   imported data (12 equipment types total, `sled` among them).
4. **Media licensing** — still an open product-owner decision; unchanged from §1.6.
5. **RU/UZ exercise content is not populated — the most consequential open gap.** The app's UI
   chrome (navigation, forms, buttons, bot messages) is fully localized in all three languages via
   next-intl and the bot's `locales/` package. Exercise **names and instructions**, however, are
   only seeded in English (`exercise_translations`: 1323 EN rows, 0 RU rows, 0 UZ rows) — exactly
   as §5 anticipated ("`ru` and `uz` rows are not created by the importer"), but the admin
   enrichment workflow that was meant to backfill them was never built (admin CRUD in general was
   descoped after Phase 4 to stay focused on the user-facing product). A Russian- or
   Uzbek-speaking user browsing exercises today sees English exercise names inside an otherwise
   fully-translated interface. Closing this gap needs either (a) a bulk AI-assisted translation
   pass over 1323 rows (feasible once an OpenAI key exists — the existing `AIProvider.structured()`
   abstraction could drive it directly) with human review before trusting it, since fitness cueing
   language needs to stay precise, or (b) the admin CRUD endpoints to let staff translate
   exercise-by-exercise. Neither is implemented yet.
6. **Frontend auth is client-side JWT, not SSR cookies.** `frontend/lib/stores/auth-store.ts`
   persists the access/refresh token pair to `localStorage` via Zustand, and every protected route
   sits behind a client component `<AuthGuard>` rather than a server-side session check. This was
   a deliberate scope choice for a JWT-bearer-token API that the Telegram bot also consumes
   directly — see the file's own comment for the reasoning — not an oversight; it does mean an XSS
   bug would be able to read the token (mitigated by never using `dangerouslySetInnerHTML`
   anywhere in the app — see `docs/SECURITY_AUDIT.md`).
7. **Telegram ↔ web account unification.** Not designed up front in this document. Resolved as:
   `POST /auth/telegram` auto-provisions or re-authenticates a bot-only account (idempotent per
   `telegram_id`, using the schema's already-nullable `password_hash` for bot-only users), and
   `POST /users/me/link-telegram` attaches an existing web account by re-validating its real
   password via the normal login path (never a new/parallel auth mechanism). A conflict (that
   Telegram ID already linked elsewhere) is a `409 TELEGRAM_ALREADY_LINKED`, tested explicitly.
8. **Rate limiting**, absent from the §2 architecture diagram, was added in Phase 9:
   `backend/app/core/rate_limit.py`, a Redis-backed fixed-window limiter on `/auth/*`, fail-open if
   Redis is down. Full writeup in `docs/SECURITY_AUDIT.md`.
9. **Redis today only backs rate-limit counters** — the §2 diagram's "Redis cache" box and the ARQ
   worker are both real (worker process runs, connects, is deployed) but nothing calls into either
   for caching or background jobs yet; `app/workers/worker.py` has a single placeholder task.
   Response caching and real background jobs (nutrition daily rollups, notification delivery) are
   future performance work, not a v1 requirement that got missed.
10. **Exercise search uses plain `ILIKE`**, not PostgreSQL full-text search (`pg_trgm`/`tsvector`).
    Simple, correct, and fast enough at 1323 rows; revisit if the exercise table grows by an order
    of magnitude or search relevance becomes a complaint.
11. **`GET /workouts` (a user's own workout list) has no pagination**, unlike the shared exercise
    list. Low severity — user-owned data, not the 1323-row shared table — deferred rather than
    fixed; see `docs/SECURITY_AUDIT.md`'s pagination section for the full reasoning.
12. **Telegram Mini App (Web App), added post-Phase-10** — the bot's primary entry point is now a
    single "Open App" button (`/start`, and the persistent chat menu button set in `bot/main.py`)
    that launches the frontend *inside Telegram* as a Web App, rather than a text-command
    conversation. Everything — workouts, nutrition, AI coach, progress, language — happens in that
    embedded page from there; the original text/FSM handlers (`bot/handlers/*.py`) are left intact
    and still work standalone, but are no longer the primary UX.
    - **Auth.** `frontend/components/telegram/telegram-webapp-gate.tsx` reads
      `Telegram.WebApp.initData` on load and posts it to `POST /auth/telegram-webapp`, which
      recomputes Telegram's own HMAC signature over it (`backend/app/core/telegram_webapp.py`,
      per Telegram's documented algorithm) before trusting anything inside — this is the
      difference from the bot-side `/auth/telegram`: that one is trusted because only our bot
      process (reading real Telegram updates) can call it, whereas `initData` arrives from
      client-side JS and could otherwise be forged with an arbitrary `telegram_id`. Both funnel
      into the same account-provisioning core (`auth_service._telegram_login_or_provision`) so a
      person gets the same account whether they open the bot or the Mini App first.
    - **Single-origin proxy, not two public URLs.** The browser inside Telegram only ever talks to
      the frontend's own origin — `frontend/next.config.mjs` proxies `/api/v1/*` server-side to
      `BACKEND_INTERNAL_URL` (the Docker-internal `http://backend:8000` by default). This means
      testing the Mini App needs exactly **one** public HTTPS tunnel, on the frontend's port, not
      a separate one for the backend too.
    - **Local testing (e.g. via ngrok):** `ngrok http 3000`, then set `FRONTEND_URL` in the root
      `.env` to the `https://*.ngrok-free.app` (or reserved-domain) URL ngrok prints, and restart
      the `telegram-bot` service (`docker compose restart telegram-bot`) so it picks up the new
      button URL — no image rebuild needed, it's a plain env var. A free ngrok tunnel's URL
      changes on every restart unless a reserved domain is configured, so this is a repeat-each-
      session step for local testing; a real deployment behind a stable domain removes it.
    - **Not done:** Telegram theme params (`Telegram.WebApp.themeParams`) aren't applied to the
      frontend's own color tokens — the app just renders in its normal dark theme regardless of
      the user's Telegram theme. Cosmetic, not functional.
