# Telegram Web App First — Audit & O'zgartirish Rejasi

> Status: **AUDIT ONLY — kod o'zgartirilmagan.** Bu hujjat yangi TZ ("Telegram Mini App first")
> ni mavjud kodbaza bilan solishtirib chiqadi. Har bir o'zgartirilishi kerak bo'lgan fayl ichida
> `TODO(webapp-first):` bloki qo'yilgan — implementatsiya keyingi bosqichda shu bloklar bo'yicha
> qilinadi. Hech qanday mavjud funksionallik hozircha buzilmagan.
>
> Sana: 2026-09-03 · Branch: `claude/telegram-webapp-first-arch-q07u9t`

---

## 0. Qisqacha xulosa

Loyihada backend (FastAPI + Postgres + Redis + ARQ), bot (aiogram 3) va frontend (Next.js 15 App
Router + next-intl + TanStack Query + Zustand) allaqachon ishlaydigan holatda. Telegram Mini App
uchun **poydevor qo'yilgan**: `/start` da `web_app` tugmasi bor (`bot/handlers/start.py`),
`initData` HMAC validatsiyasi to'g'ri yozilgan (`backend/app/core/telegram_webapp.py`), va
frontendda avtomatik login gate bor (`frontend/components/telegram/telegram-webapp-gate.tsx`).

Ya'ni TZ ni noldan qilish shart emas — **arxitektura burilishi** kerak. Asosiy farq:

| | Hozir | TZ talab qiladi |
|---|---|---|
| Bot roli | To'liq ikkinchi UI (workouts, nutrition, AI, progress — 1171 qator handler) | Faqat entry point + notification |
| Frontend layout | Desktop sidebar (`grid-cols-[16rem_1fr]`) | Mobile-first + bottom nav + AI FAB |
| Theme | Qattiq `class="dark"` | Telegram theme (light/dark + `--tg-theme-*`) |
| Onboarding | Yo'q | 12 qadamli WebApp wizard + BMR/TDEE |
| Food analyzer | Faqat URL bo'yicha AI chaqiruv, UI yo'q | Kamera/upload + natija kartalari + diary |
| Telegram SDK | `ready()` + `expand()` | BackButton, MainButton, theme, haptics, `start_param` |
| AI xarajat nazorati | Yo'q | Rate limit, kunlik limit, token/cost tracking |

Jami: **~35 ta mavjud fayl o'zgaradi**, **~30 ta yangi fayl** qo'shiladi.

---

## 1. 🔴 BLOCKER — xavfsizlik (birinchi navbatda tuzatiladi)

### 1.1 `POST /api/v1/auth/telegram` — autentifikatsiyasiz akkaunt egallash

`backend/app/api/v1/auth.py:34` → `auth_service.telegram_auth()` hech qanday imzo tekshirmasdan,
body dagi `telegram_id` bo'yicha JWT beradi:

```python
async def telegram_auth(db, data: TelegramAuthRequest) -> TokenResponse:
    return await _telegram_login_or_provision(db, telegram_id=data.telegram_id, ...)
```

Bu endpoint faqat bot ichkarida chaqiradi degan taxminga asoslangan, lekin **hech narsa uni
tashqaridan chaqirishdan to'smaydi**. Backend porti publicga ochilsa (yoki kimdir Docker
tarmog'iga kirsa), istalgan odam `{"telegram_id": 123456789}` yuborib, o'sha foydalanuvchi
sessiyasini oladi. TZ §28 aynan shuni taqiqlaydi: *"Never trust frontend-provided Telegram user
information."*

**Yechim (ertaga):** ikkita variantdan biri —
1. Bot va backend o'rtasida shared secret (`INTERNAL_API_KEY` header), yoki
2. Endpointni butunlay olib tashlab, bot ham `initData`-siz emas, `TelegramUser` ni faqat
   `link` oqimi orqali yaratish.

Tavsiya: (1) — kam invaziv, botning mavjud oqimlarini buzmaydi.

### 1.2 `initData` yashash muddati 24 soat

`backend/app/core/telegram_webapp.py:27` — `_MAX_AGE_SECONDS = 24 * 60 * 60`. Telegram o'zi
muddat qo'ymaydi, bu bizning replay oynamiz. 24 soat juda keng: qo'lga tushgan `initData`
string bir kun davomida ishlaydi. **Tavsiya:** default 1 soat, `settings` orqali sozlanadigan.

### 1.3 AI endpointlarida limit yo'q

`backend/app/api/v1/ai.py` — 4 ta endpoint, birortasida `rate_limit` yo'q. Vision chaqiruvlari
(`/nutrition/analyze-image`) eng qimmati. TZ §32 talab qiladi: per-user kunlik limit, token
tracking, cost tracking. Hozirgi `backend/app/core/rate_limit.py` faqat **IP** bo'yicha ishlaydi —
per-user variant kerak.

---

## 2. Bot — to'liq UI dan entry point ga qisqartirish (TZ §2, §3, §4, §43, §45)

Hozir bot ichida ikkinchi to'liq mahsulot bor. TZ buni aniq taqiqlaydi.

| Fayl | Qator | Nima qilinadi |
|---|---|---|
| `bot/handlers/start.py` | 88 | Welcome matnini TZ §3 dagi to'liq uch tilli (uz/ru/en) versiyaga almashtirish; til foydalanuvchi profilidan / `message.from_user.language_code` dan olinadi; deep-link (`/start workout`) parsing qo'shish |
| `bot/handlers/workouts.py` | 299 | ⚠️ Eng katta dublikat. FSM bilan workout yaratish, set logging — hammasi WebApp da bor. → "Open in GYM App" stub |
| `bot/handlers/nutrition.py` | 135 | Meal logging FSM → stub. Photo handler → TZ §18: "Food analysis is available in GYM App" + tugma |
| `bot/handlers/exercises.py` | 48 | Exercise search → stub (`startapp=exercises`) |
| `bot/handlers/progress.py` | 61 | → stub (`startapp=progress`) |
| `bot/handlers/ai_coach.py` | 62 | → stub (`startapp=ai`) |
| `bot/handlers/profile.py` | 64 | Til almashtirish qoladi (fallback), qolgani → stub |
| `bot/keyboards/main_menu.py` | 15 | 7 tugmali reply keyboard → bitta WebApp tugmasi |
| `bot/keyboards/workouts.py`, `nutrition.py` | 33 | Handlerlar bilan birga o'chadi |
| `bot/main.py` | 57 | `BOT_COMMANDS` 8 tadan 4 taga: `/start`, `/app`, `/help`, `/settings` |
| `bot/locales/{uz,ru,en}.py` | 234 | Yangi welcome/notification stringlari; eskilarini olib tashlash |
| `bot/handlers/link.py` | 62 | O'zgarmaydi — TZ §7 "account linking" ni qo'llab-quvvatlaydi |
| `bot/tests/*` | — | `test_workouts_handler.py`, `test_nutrition_handler.py`, `test_ai_coach_handler.py` stub oqimga moslanadi |

**Muhim qaror:** eski handlerlarni o'chirib tashlash o'rniga `bot/handlers/legacy/` ga ko'chirib,
`ENABLE_LEGACY_BOT_UI=false` flagi ortiga yashirish tavsiya etiladi. Sabab: `FRONTEND_URL` hali
sozlanmagan (HTTPS tunnel yo'q) muhitda bot butunlay ishlamay qolmaydi. TZ §2 ni buzmaydi, chunki
default holatda o'chiq.

### Yetishmayotgan bot funksiyalari

- **Notification yuborish yo'q** (TZ §25). `backend/app/workers/worker.py` — `noop` dan boshqa
  hech narsa yo'q. Kerak: ARQ cron jobs (workout reminder, nutrition reminder, weekly progress) +
  botga `POST /internal/notify` yoki bot ichida Telegram API chaqiruvi.
- **Deep link yo'q** (TZ §24). `startapp`/`start_param` hech qayerda ishlatilmagan (grep: 0 natija).

---

## 3. Backend (TZ §5, §7, §26, §29, §32, §33)

### 3.1 O'zgaradigan fayllar

| Fayl | Nima qilinadi |
|---|---|
| `backend/app/api/v1/auth.py` | §1.1 fix; `/telegram-webapp` ni `/telegram` bilan bir xil hujjatlash (TZ §5 `/auth/telegram` deydi — pastda "TZ tuzatishlari" ga qarang) |
| `backend/app/core/telegram_webapp.py` | Max-age 1 soat + sozlanadigan; `start_param` ni parse qilib qaytarish (deep link uchun) |
| `backend/app/models/user.py` | `User.avatar_url` qo'shish (TZ §7); `username` NOT NULL ekanligi Telegram-only user uchun sintetik username majburlaydi — nullable qilish; `UserProfile` ga `training_days_per_week`, `available_equipment` (JSONB), `onboarding_completed` |
| `backend/app/schemas/user.py` | Yuqoridagi maydonlar + `OnboardingRequest` |
| `backend/app/api/v1/users.py` | `POST /users/me/onboarding` (12 qadam natijasi, BMR/TDEE hisoblab qaytaradi) |
| `backend/app/api/v1/ai.py` | Per-user rate limit; SSE streaming variant `/ai/chat/stream` (TZ §16) |
| `backend/app/api/v1/nutrition.py` | `POST /nutrition/analyze-image` hozir faqat `image_url` qabul qiladi → multipart file upload kerak (TZ §17, §20 kamera) |
| `backend/app/services/ai_service.py` | Token/cost tracking; kunlik limit; TZ §33 — AI faqat ovqatni **aniqlaydi**, kaloriya qiymatlari nutrition DB dan olinadi |
| `backend/app/core/rate_limit.py` | Per-user (nafaqat per-IP) limiter |
| `backend/app/api/v1/router.py` | Yangi routerlar: `notifications`, `favorites`, `admin` |
| `backend/app/workers/worker.py` | Real joblar: reminder cron, nutrition rollup, notification delivery |
| `backend/app/core/config.py` | `INTERNAL_API_KEY`, `INIT_DATA_MAX_AGE`, `AI_DAILY_LIMIT`, S3 sozlamalari |
| `backend/scripts/import_exercises.py` | `thumbUrl` → `image_url` ✅ allaqachon to'g'ri (101-qator) |

### 3.2 Yangi fayllar

- `backend/app/services/onboarding_service.py` — BMR (Mifflin-St Jeor), TDEE, makro taqsimoti.
  **Hozir loyihada BMR/TDEE hisobi umuman yo'q** (grep: 0 natija), TZ §14 step 12 buni talab qiladi.
- `backend/app/api/v1/notifications.py` — TZ §29 (`Notification` modeli bor, router yo'q)
- `backend/app/api/v1/favorites.py` — TZ §29 (hozir `exercises.py` ichida)
- `backend/app/api/v1/admin.py` — AI usage dashboard (TZ §32)
- `backend/app/services/storage_service.py` — S3 abstraksiya (`.env.example` da `STORAGE_*`
  o'zgaruvchilari bor, lekin hech qayerda ishlatilmaydi)
- `backend/app/services/nutrition_db.py` — TZ §33 uchun oziq-ovqat qiymatlari bazasi
- `backend/app/models/ai_usage.py` yoki `models/ai.py` ga qo'shimcha — token/cost log
- Migration: yuqoridagi ustunlar uchun (`alembic revision`)

---

## 4. Frontend — eng katta ish (TZ §8–§22, §30, §39–§41)

### 4.1 Layout va navigatsiya

`frontend/app/[locale]/(app)/layout.tsx` — hozir `grid-cols-[16rem_1fr]`, ya'ni **doim** desktop
sidebar. Telefonda ham 16rem sidebar chiqadi. TZ §8/§39 mobile-first talab qiladi.

- `(app)/layout.tsx` → mobil: bottom nav + content; `lg:` dan boshlab sidebar
- Yangi `components/nav/bottom-nav.tsx` — 🏠 Home / 🏋️ Workout / 💪 Exercises / 🍎 Nutrition / 👤 Profile
- Yangi `components/ai/ai-fab.tsx` — floating AI tugmasi
- `components/dashboard/sidebar-nav.tsx` — faqat desktopda ko'rinadi, `settings`/`profile`
  linklari qo'shiladi

### 4.2 Telegram SDK integratsiyasi

`frontend/components/telegram/telegram-webapp-gate.tsx` (87 qator) hozir faqat `ready()`,
`expand()` va login qiladi. TZ §9, §10, §21, §22 uchun kengaytirish kerak:

- `lib/telegram/sdk.ts` — tiplangan wrapper (hozir `declare global` gate ichida turibdi)
- `lib/telegram/use-back-button.ts` — TZ §21
- `lib/telegram/use-main-button.ts` — TZ §22
- `lib/telegram/use-haptics.ts` — TZ §9 ("ortiqcha ishlatmang")
- `lib/telegram/theme.ts` — `themeParams` → CSS o'zgaruvchilar (TZ §10)
- Gate ichida: `initDataUnsafe.start_param` o'qish → tegishli sahifaga yo'naltirish (TZ §24)
- Gate ichida: `onboarding_completed === false` → `/onboarding` ga (TZ §14)

### 4.3 Theme

`frontend/app/[locale]/layout.tsx:32` — `<html className="dark">` qattiq yozilgan.
`frontend/app/globals.css` — faqat dark palitra. TZ §10 light + dark + `--tg-theme-*` talab qiladi.

- `globals.css` — `:root` (light) + `:root[data-theme="dark"]`, va `--tg-theme-*` ni o'z
  tokenlarimizga bog'lovchi qatlam
- `tailwind.config.ts` — safe-area inset utilitalari (bottom nav uchun)
- `layout.tsx` — `viewport-fit=cover`, PWA manifest, `themeColor`

### 4.4 Yetishmayotgan sahifalar (TZ §11)

| Route (TZ) | Hozir | Holat |
|---|---|---|
| `/[locale]/onboarding` | — | 🔴 **Butunlay yo'q** — 12 qadam, TZ §14 |
| `/[locale]/nutrition/analyze` | — | 🔴 **Yo'q** — TZ §17, eng muhim feature |
| `/[locale]/nutrition/history` | — | 🔴 Yo'q |
| `/[locale]/workouts/create` | dialog | 🟡 `create-workout-dialog.tsx` bor, alohida sahifa yo'q |
| `/[locale]/profile` | — | 🔴 Yo'q |
| `/[locale]/settings` | — | 🔴 Yo'q (notification sozlamalari shu yerda — TZ §25) |
| `/[locale]/ai` | `/ai-coach` | 🟡 Nomi boshqa; suggested questions, streaming yo'q |
| `/[locale]/exercises/[slug]` | `[id]` | 🟡 "TZ tuzatishlari" ga qarang |
| `/[locale]/workout/[sessionId]` | `workouts/[id]/session` | 🟡 Ishlaydi, TZ boshqa yo'l taklif qiladi |
| `/[locale]/progress` | ✅ bor | |

### 4.5 Performance (TZ §30, §31)

`frontend/app/[locale]/(app)/exercises/page.tsx:110` — ro'yxatda **to'liq GIF** yuklanadi:

```tsx
<img src={ex.gif_url} alt={ex.name} loading="lazy" />
```

Backend `ExerciseSummary` da `image_url` (= `thumbUrl`) allaqachon bor va import ham qilingan.
Ro'yxatda `image_url`, detalda `gif_url` bo'lishi kerak — TZ §31. Bu bir qatorlik fix, lekin
1323 ta mashq uchun katta farq.

### 4.6 Boshqa frontend ishlar

| Fayl | Nima qilinadi |
|---|---|
| `lib/api-client.ts` | Multipart (rasm yuklash) qo'llab-quvvatlash; 401 da Telegram ichida bo'lsa `initData` bilan jimgina qayta login (hozir refresh muvaffaqiyatsiz bo'lsa `/login` ga uloqtiradi — Mini App ichida bu boshi berk ko'cha) |
| `components/auth/auth-guard.tsx` | Telegram ichida `/login` ga redirect qilmaslik; onboarding tekshiruvi |
| `lib/stores/auth-store.ts` | `onboarding_completed` holati |
| `lib/types.ts` | Yangi tiplar: onboarding, food analysis, notifications |
| `messages/{uz,ru,en}.json` | Yangi kalitlar: onboarding (12 qadam), analyzer, bottom nav, settings, AI suggestions — TZ §36 |
| `middleware.ts` | Telegram `language_code` → locale mapping (TZ §11) |
| `public/` | PWA: `manifest.json`, ikonalar, service worker (TZ §40) — hozir faqat `.gitkeep` |
| `package.json` | Ehtimol `@telegram-apps/sdk`; offline sync uchun IndexedDB kutubxonasi (TZ §41) |
| `e2e/happy-path.spec.ts` | Yangi oqim: Telegram gate → onboarding → dashboard |

---

## 5. Infratuzilma va hujjatlar

| Fayl | Nima qilinadi |
|---|---|
| `.env.example` | `INTERNAL_API_KEY`, `INIT_DATA_MAX_AGE_SECONDS`, `AI_DAILY_LIMIT_PER_USER`, `NEXT_PUBLIC_*` |
| `docker-compose.yml` | Nginx reverse proxy (TZ §27); worker uchun cron |
| `docs/ARCHITECTURE.md` | WebApp-first ga qayta yozish |
| `docs/TELEGRAM_WEBAPP.md` | 🔴 **Yangi** — TZ §46 Phase 3 talab qiladi |
| `docs/AUTHENTICATION.md` | 🔴 **Yangi** — TZ §46 Phase 3 |
| `docs/API.md`, `docs/DATABASE.md`, `docs/IMPLEMENTATION_PLAN.md` | Yangilash |
| `README.md` | Mini App quickstart (ngrok + BotFather sozlash) |

---

## 6. TZ dagi kamchiliklar / tuzatishlar

TZ ruxsat berganidek ("TZ da kamchilik bo'lsa o'zing to'g'irlashing mumkin"), quyidagilarni
tuzatish tavsiya etiladi:

1. **§5 endpoint nomi.** TZ `POST /api/v1/auth/telegram` ni `initData` uchun deydi, lekin bu nom
   loyihada allaqachon **bot** oqimi uchun band. `/auth/telegram-webapp` nomini saqlab qolish
   aniqroq — aks holda ikkita butunlay boshqacha ishonch modeli bitta URL da aralashib ketadi.
   *(Muqobil: `/auth/telegram` ni WebApp ga berib, bot oqimini `/auth/telegram-bot` ga ko'chirish
   — lekin bu botni buzadi.)*

2. **§11 `/exercises/[slug]`.** Ma'lumotlar bazasida `slug` unikal emas — `id` maydoni
   `"abductors/lever-seated-hip-abduction"` ko'rinishida (muscle prefiksi bilan), `slug` esa
   faqat `"lever-seated-hip-abduction"`. Ikki mushak guruhida bir xil slug bo'lishi mumkin.
   Tavsiya: URL da UUID yoki to'liq `id` qolsin, `slug` faqat SEO uchun qo'shimcha bo'lsin.

3. **§14 onboarding 12 qadam** — mobil uchun juda uzun. Tavsiya: 12 ta ekran o'rniga 6 ta
   guruhlangan ekran (til → shaxsiy ma'lumot → maqsad → tajriba+chastota → jihoz+faollik →
   natija). Bir xil ma'lumot, ikki barobar kam tap. TZ ning maqsadi (§37 "fast startup") aynan
   shuni talab qiladi.

4. **§33 nutrition database.** TZ "AI ni nutrition database sifatida ishonmang" deydi va bu
   to'g'ri, lekin loyihada hozir hech qanday oziq-ovqat bazasi yo'q. Bu alohida katta ish
   (USDA FDC yoki Open Food Facts integratsiyasi). Tavsiya: birinchi bosqichda AI qiymatlarini
   ishlatib, lekin `confidence` va "taxminiy" belgisi bilan ko'rsatish; nutrition DB ni alohida
   faza sifatida rejalashtirish. Aks holda food analyzer bloklanadi.

5. **§32 admin dashboard** — MVP uchun ortiqcha. Birinchi bosqichda token/cost ni `ai_usage`
   jadvaliga yozish va limitni majburlash yetarli; dashboard keyinroq.

6. **§40 PWA + §41 offline** — Telegram Mini App ichida service worker cheklangan ishlaydi.
   Offline set logging ni service worker orqali emas, IndexedDB + queue orqali qilish tavsiya
   etiladi (TZ §41 ning maqsadi shunda ham bajariladi).

7. **§48 "birinchi ExerciseGymGifsDB repositoriysini tekshiring"** — bu allaqachon bajarilgan:
   `data/exercises/exercises.en.json` da 1323 ta mashq bor (id, slug, name, muscle, bodyPart,
   equipment, category, secondaryMuscles, instructions, gifUrl, thumbUrl), va
   `backend/scripts/import_exercises.py` ularni bazaga yuklaydi. Qayta tahlil qilish shart emas.

---

## 7. Bajarish tartibi (ertaga)

1. **Xavfsizlik** — §1.1, §1.2, §1.3 (yarim kun)
2. **Backend model + onboarding service + migration** — §3
3. **Frontend shell**: theme, mobile layout, bottom nav, Telegram SDK hooks — §4.1–4.3
4. **Onboarding wizard** — TZ §14
5. **Food analyzer** (backend upload + frontend kamera UI) — TZ §17, §20
6. **Bot qisqartirish + deep links + notifications** — §2
7. **Performance**: thumbnail fix, code splitting — §4.5
8. **Docs + testlar**

1–3 qadamlar bir-biriga bog'liq va ketma-ket; 4–6 parallel qilinishi mumkin.
