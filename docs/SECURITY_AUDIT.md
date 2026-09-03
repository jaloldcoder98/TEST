# Security & performance audit (Phase 9)

Walk-through against spec.md §37 (auth/security) and §40 (data volume/performance), checked
against the actual implementation rather than the plan. Format: finding, verdict, what was done.

## Auth & tokens

- **JWT access + refresh, separate signing secrets.** `app/core/security.py` signs access and
  refresh tokens with distinct secrets (`jwt_secret` / `jwt_refresh_secret`), so a leaked access
  token can't be used to forge a refresh token or vice versa. **Verdict: correct, no action.**
- **Refresh token rotation and revocation.** `RefreshToken` rows store a SHA-256 hash of the
  token, never the raw value (`app/core/security.py:hash_token`) — a database dump alone can't be
  replayed as a bearer token. `auth_service.refresh()` revokes the used token and issues a new
  pair on every call (single-use rotation); `logout()` revokes on demand. Covered by
  `tests/test_auth.py`. **Verdict: correct, no action.**
- **Password hashing.** bcrypt via passlib (`CryptContext(schemes=["bcrypt"])`), no custom crypto.
  **Verdict: correct, no action.**
- **Brute-force / credential stuffing on `/auth/login`, `/auth/register`, `/auth/refresh`,
  `/auth/telegram`.** These had **no rate limiting at all** before this pass — an attacker could
  script unlimited login attempts against any username. **Fixed:** `app/core/rate_limit.py` adds
  a Redis-backed, fixed-window, per-client-IP limiter (login/register: 10 req/min, refresh/
  telegram-auth: 30 req/min — generous for a real client's normal token-rotation traffic, tight
  enough to blunt scripted guessing) wired onto all four endpoints via FastAPI's `dependencies=`.
  Fails open (allows the request) if Redis is unreachable, logging a warning, rather than taking
  auth down if the cache is degraded — a rate limiter should never itself become the outage.
  Covered by `tests/test_rate_limit.py` (7 tests: under/over limit, per-IP scoping, per-endpoint
  scoping, the settings kill-switch, the fail-open path, and one true end-to-end HTTP test against
  `/auth/login`).

## SQL injection surface

Grepped the entire backend for raw SQL (`text(...)`, string-built queries): **zero matches**.
Every query goes through SQLAlchemy's async ORM with bound parameters — including the
`func.random()` candidate pool for AI workout generation and the `ILIKE` food-item lookups, which
are exactly the kind of query someone might be tempted to hand-build a string for. **Verdict:
no SQL injection surface exists.**

## Cross-user data isolation

Every resource scoped to a user (workouts, workout sessions, nutrition logs, body measurements,
AI conversations) filters by `user_id` at the query level, and the test suite includes explicit
"user A can't touch user B's data" cases: `test_workouts.py::test_cannot_access_another_users_workout`,
`test_ai.py::test_chat_rejects_another_users_conversation_id`, and the Telegram account-linking
conflict check (`link_telegram` raises `TELEGRAM_ALREADY_LINKED` rather than silently reattaching
someone else's account). **Verdict: correct, tested.**

## File uploads

Spec calls for MIME/size/dimension validation on uploaded files. **This doesn't apply yet** — the
food-photo analyzer takes an `image_url` (a link to an already-hosted image), not a multipart
file upload; there is no `UploadFile`/`File()` endpoint anywhere in the API. Object storage
settings (`storage_endpoint` etc.) exist in config for a future direct-upload flow but nothing
uses them yet. **Verdict: not a gap — the feature that would need this validation doesn't exist
yet. Revisit if/when direct photo upload replaces URL-based analysis.**

## Pagination / response size

- Exercise list (`GET /exercises`, 1323 rows total): `pageSize` is bounded server-side
  (`Query(le=settings.max_page_size)`, default 20 / max 100) — a client cannot request the whole
  table in one response. **Verdict: correct.**
- `GET /workouts` (a user's own workouts) has **no pagination** — it returns the full list in one
  response. **Verdict: low severity, deferred.** This is user-owned data (not a cross-user or
  public dataset), and nothing in this app's usage pattern produces thousands of workouts per
  user the way the shared exercise table does. Worth paginating if usage ever suggests otherwise,
  but not urgent enough to justify a breaking response-shape change (array → `{items, total}`)
  during this audit pass.

## Redis / caching

Redis is a configured dependency (`docker-compose.yml`, `settings.redis_url`) but nothing reads
from a cache today — the `arq` worker (`app/workers/worker.py`) has no real jobs registered yet,
and every API read hits Postgres directly. Since nothing is cached, "never key a cache entry by
anything user-private" (spec §40) is trivially satisfied — there's no cache to leak through. Redis
is now also used for rate-limit counters (`ratelimit:<key>:<ip>`), which are IP-keyed, not
user-keyed, and expire within 60s. **Verdict: no caching implemented, no privacy issue, deferred
as a performance optimization rather than a security gap** — the app is correct without it, just
not as fast as it could be under heavy read load.

## CORS

`CORSMiddleware` uses `allow_origins` from `CORS_ORIGINS` (env-configurable, defaults to
`http://localhost:3000` in dev, never `"*"`) with `allow_credentials=True`. Starlette itself
refuses to combine a wildcard origin with credentials, so this can't silently regress into an
open CORS policy. **Verdict: correct — just make sure `CORS_ORIGINS` is set to the real frontend
origin(s) in production** (see docs root `README.md` / Phase 10 deployment notes).

## Logging / secrets

- No application code logs request bodies, passwords, or tokens. SQL echo logging
  (`echo=settings.debug`) is tied to `DEBUG`, which must be `false` in production — it currently
  defaults to `true` for local dev convenience.
- No secret is hardcoded anywhere in the codebase; every credential (`JWT_SECRET`,
  `JWT_REFRESH_SECRET`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, storage keys) comes from the
  environment with non-secret local-dev defaults or `None`. `.env`, `.env.local`, and
  `.env.*.local` are all gitignored; confirmed via `git ls-files` that no `.env*` file is tracked
  anywhere in this repo.
- **Action for Phase 10 / deployment:** production `.env` must set real, unique `JWT_SECRET` /
  `JWT_REFRESH_SECRET` values (never the `change-me-in-.env` dev defaults) and `DEBUG=false`.

## Frontend

- No `dangerouslySetInnerHTML` anywhere in application code (only inside `node_modules` type
  definitions, unused). React's default escaping handles all user-provided text (usernames,
  workout names, food descriptions, AI chat replies).
- JWTs live in `localStorage` via Zustand's `persist` middleware — a deliberate, documented
  tradeoff (see `frontend/lib/stores/auth-store.ts`) for a client-only SPA dashboard rather than
  an httpOnly-cookie/SSR-session architecture. This means an XSS bug would be able to read the
  token; the mitigation is the "no `dangerouslySetInnerHTML`, no unsanitized third-party HTML
  injection" property above, not the storage mechanism itself.

## Summary of changes made this pass

1. Added `app/core/rate_limit.py` (Redis-backed, fail-open, per-IP-per-endpoint fixed window).
2. Wired it onto `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/telegram`.
3. Added `RATE_LIMIT_ENABLED` setting (default `true`; test suite forces it `false` since every
   test shares one client IP, with a dedicated test file re-enabling it to test the limiter
   itself).
4. `tests/test_rate_limit.py` — 7 new tests. Backend suite: 50/50 passing, `ruff check` clean.

Everything else in this document is a **verdict**, not a change: most of the implementation
already matched spec, with the rate-limiting gap being the one real security fix this pass made.
