# GYM Platform — API Specification

Base path: `/api/v1`. JSON in/out. Errors always in the shape from spec §43:

```json
{ "success": false, "error": { "code": "EXERCISE_NOT_FOUND", "message": "Exercise not found" } }
```

Auth: `Authorization: Bearer <access_token>` (JWT). All endpoints except `/auth/*`,
`/exercises*` (read-only catalog) and `/health` require auth. A user can only ever read/write
their own `user_id`-scoped rows — enforced in the repository layer, not just the route.

## Auth
- `POST /auth/register` — email/password or Telegram init-data. Returns access + refresh token.
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout` — revokes the refresh token.

## Users
- `GET /users/me`
- `PATCH /users/me` — profile fields (spec §12).

## Exercises (public read)
- `GET /exercises?muscle=&equipment=&bodyPart=&category=&q=&page=&pageSize=` — paginated,
  default 20–30/page (spec §40 — never return the full 1323 by default).
- `GET /exercises/{id}`
- `GET /exercises/search?q=` — fuzzy, multilingual (pg_trgm).
- `GET /exercises/muscles`
- `GET /exercises/equipment`
- `GET /exercises/body-parts`
- `GET /exercises/categories`
- `POST /exercises/{id}/favorite` / `DELETE /exercises/{id}/favorite`

## Workouts
- `GET /workouts` · `POST /workouts` · `GET /workouts/{id}` · `PATCH /workouts/{id}` ·
  `DELETE /workouts/{id}`
- `POST /workouts/{id}/start` → creates a `workout_session`
- `POST /workout-sessions/{id}/sets` — log a set
- `POST /workout-sessions/{id}/finish` — computes total volume/sets/reps/duration/est. calories,
  checks for new personal records

## Nutrition
- `GET /nutrition/today`
- `POST /nutrition/log` — manual entry
- `POST /nutrition/analyze-image` — multipart (`image`, optional `portion_size`,
  `description`); response shape is the one in spec §17.
- `GET /nutrition/history?from=&to=`

## AI
- `POST /ai/chat` — general fitness/nutrition Q&A, streams or returns structured data per
  spec §15/§16.
- `POST /ai/workout` — generate a workout from goal/equipment/days/duration; exercises are
  looked up from the DB first, never invented (spec §51).
- `POST /ai/nutrition` — nutrition Q&A backed by `food_items` where possible.
- `POST /ai/food-analysis` — same pipeline as `/nutrition/analyze-image`, exposed separately for
  the Telegram bot's async flow.

## Progress
- `GET /progress` — dashboard summary (weight trend, workout frequency, volume trend).
- `POST /progress/weight`
- `POST /progress/measurements`

## Admin (spec §38, requires `is_admin`)
- `GET/PATCH /admin/exercises/{id}` — edit translations, deactivate exercises.
- `GET/POST/PATCH /admin/food-items`
- `GET/PATCH /admin/prompts` — edit AI prompt templates without a deploy.
- `GET /admin/analytics` — DAU/WAU, workout counts, AI usage, most-popular exercises (spec §39).

## Rate limits (spec §37)
Per-user token-bucket on `/ai/*` (expensive) and a broader IP-based limit on `/auth/*`
(brute-force protection). Exact numbers are a Phase 4 config decision, not fixed here.

## Caching (spec §40)
Redis, keyed by language: exercise lists/filters, muscle/equipment/body-part/category lookups,
"popular exercises". Never cache anything under a `user_id`-scoped key path here — that belongs
to per-request auth, not the shared cache.
