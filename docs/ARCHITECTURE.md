# GYM Platform — Architecture

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
