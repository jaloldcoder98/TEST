# Hevy TMA — Workout Tracker (Telegram Mini App)

Hevy uslubidagi mashg'ulot tracker: Telegram Mini App sifatida ishlaydigan
set/reps/weight/RPE loggeri, dam olish taymeri, 1300+ mashqli kutubxona va
shaxsiy rekordlar (PR).

**Stack:** React 18 + Vite + Tailwind + `@twa-dev/sdk` · Node 22 + Express 4 +
Zod · PostgreSQL 16 + Prisma 5 · TypeScript (strict) hamma joyda.

> Bu papka repozitoriyaning mavjud FastAPI/Next.js `GYM Platform` xizmatlaridan
> **mustaqil**. O'z `package.json`, `docker-compose.yml` va DB'siga ega, faqat
> `data/exercises/` datasetini birgalikda ishlatadi.

---

## Tez boshlash

```bash
cd apps/hevy-tma
npm install                                  # workspaces: server + web

cp server/.env.example server/.env           # DATABASE_URL, TELEGRAM_BOT_TOKEN
cp web/.env.example web/.env                 # VITE_API_BASE_URL

npm run migrate -w @hevy-tma/server          # Prisma migratsiyalari
npm run seed                                 # 1323 ta mashqni import qiladi

npm run dev:server                           # http://localhost:4000
npm run dev:web                              # http://localhost:5173
```

Docker bilan:

```bash
TELEGRAM_BOT_TOKEN=<bot-token> docker compose up --build
docker compose exec server npm run seed
```

### Telegram'ga ulash

1. [@BotFather](https://t.me/BotFather) → `/newapp` → Mini App yarating.
2. Web App URL sifatida **HTTPS** manzil bering. Lokal ishlab chiqishda tunnel
   kerak: `cloudflared tunnel --url http://localhost:5173`.
3. Server `.env` ichidagi `CORS_ORIGINS` ga o'sha manzilni qo'shing.

Telegramsiz (oddiy brauzerda) sinash uchun serverda `AUTH_DEV_BYPASS=true`
qo'ying — imzo tekshiruvi o'tkazib yuboriladi va `DEV_TELEGRAM_ID` foydalanuvchi
sifatida kirasiz. `NODE_ENV=production` bo'lsa server bu bayroq bilan
umuman ishga tushmaydi.

---

## Arxitektura

```
Telegram client
      │  initData (HMAC-SHA256 imzolangan)
      ▼
React (Vite)  ──X-Telegram-Init-Data──►  Express API  ──Prisma──►  PostgreSQL
  @twa-dev/sdk                            telegramAuth
  TanStack Query                          zod validation
  zustand (+localStorage draft)           PR hisoblash
```

Har bir so'rovda `initData` qayta tekshiriladi — server sessiya saqlamaydi,
JWT ham yo'q. Foydalanuvchi `telegramId` bo'yicha upsert qilinadi, ya'ni
alohida ro'yxatdan o'tish bosqichi kerak emas.

```
server/
  prisma/schema.prisma        User · Exercise · Workout · WorkoutExercise · WorkoutSet · PersonalRecord
  prisma/seed.ts              data/exercises/ → Exercise jadvali (idempotent)
  src/config/env.ts           zod bilan tekshiriladigan env
  src/lib/telegram-init-data.ts   imzo tekshiruvi (framework'siz, testlangan)
  src/middleware/             telegramAuth · error-handler · validate · async-handler
  src/modules/workouts/       schema → service → controller → routes
  src/modules/exercises/      kutubxona qidiruvi, filtrlar, custom mashqlar
  src/modules/stats/          umumiy statistika + haftalik hajm + PR ro'yxati
  tests/                      init-data unit testlari · API e2e testlari

web/
  src/lib/telegram.ts         @twa-dev/sdk wrapper (Telegramsiz ham ishlaydi)
  src/lib/api.ts              typed API klient, har so'rovga initData qo'shadi
  src/store/workout-store.ts  aktiv mashg'ulot (localStorage'da saqlanadi)
  src/hooks/useRestTimer.ts   absolute-timestamp countdown
  src/components/WorkoutTracker.tsx   asosiy ekran
  src/components/SetRow.tsx           Weight / Reps / RPE + ✓ tugma
  src/components/ExercisePicker.tsx   kutubxona (debounced qidiruv)
```

---

## Ma'lumotlar bazasi

| Model | Vazifasi |
|---|---|
| `User` | Telegram identifikatori (`BigInt`), til, birlik (KG/LB), default dam olish vaqti |
| `Exercise` | Kutubxona; `createdById = null` → built-in, aks holda foydalanuvchi mashqi |
| `Workout` | Sessiya + keshlangan `totalVolumeKg` / `totalSets` / `totalReps` |
| `WorkoutExercise` | Mashg'ulot ichidagi bitta mashq (`position` bo'yicha tartib) |
| `WorkoutSet` | `weightKg`, `reps`, `rpe`, `setType`, `durationSec`, `distanceM` |
| `PersonalRecord` | `(user, exercise, type)` bo'yicha bitta joriy rekord |

**Set turlari:** `WARMUP` · `NORMAL` · `DROP` · `FAILURE`.
Isinish setlari hajm (volume) va PR hisobiga **kirmaydi**.

**PR turlari:** `MAX_WEIGHT`, `MAX_REPS`, `BEST_SET_VOLUME`, `ESTIMATED_1RM`
(Epley: `w × (1 + reps/30)`, reps 12 da cheklanadi — undan yuqorisida formula
juda xato beradi).

Og'irlik doim **kilogrammda** saqlanadi; LB foydalanuvchilari uchun konvertatsiya
faqat UI darajasida. `Decimal` maydonlar API'da `number` bo'lib qaytadi
(`workout.mapper.ts`).

---

## API

Barcha `/api/*` endpointlar `X-Telegram-Init-Data` header'ini talab qiladi
(`Authorization: tma <initData>` ham qabul qilinadi).

| Method | Path | Tavsif |
|---|---|---|
| `GET` | `/health` | Auth talab qilmaydi |
| `GET` | `/api/me` | Joriy profil |
| `GET` | `/api/exercises?q=&muscleGroup=&equipment=&limit=&cursor=` | Kutubxona |
| `GET` | `/api/exercises/muscle-groups` | Filtr chiplari uchun sanoq |
| `GET` | `/api/exercises/:id` | Mashq + shu mashq bo'yicha PR'lar |
| `POST` | `/api/exercises` | Custom mashq |
| `POST` | `/api/workouts` | Mashg'ulotni saqlash → `{ workout, personalRecords }` |
| `GET` | `/api/workouts?limit=&cursor=&status=` | Tarix (cursor paginatsiya) |
| `GET` | `/api/workouts/:id` | Bitta mashg'ulot |
| `DELETE` | `/api/workouts/:id` | O'chirish |
| `GET` | `/api/stats/summary?weeks=12` | Umumiy raqamlar + haftalik hajm |
| `GET` | `/api/stats/personal-records` | Barcha joriy rekordlar |

`POST /api/workouts` misoli:

```jsonc
{
  "title": "Push Day",
  "status": "COMPLETED",
  "startedAt": "2026-09-05T09:00:00.000Z",
  "finishedAt": "2026-09-05T10:05:00.000Z",
  "exercises": [
    {
      "exerciseId": "…uuid…",
      "restSeconds": 120,
      "sets": [
        { "setType": "WARMUP", "weightKg": 40, "reps": 10, "isCompleted": true },
        { "setType": "NORMAL", "weightKg": 90, "reps": 5, "rpe": 9, "isCompleted": true }
      ]
    }
  ]
}
```

Javob `personalRecords` massivini qaytaradi — UI shu asosda "Yangi rekord!"
oynasini ko'rsatadi.

Xatolar bir xil shaklda: `{ "error": { "code", "message", "details" } }`.

---

## Testlar

```bash
cd server
npm run test:unit    # initData imzo tekshiruvi (haqiqiy HMAC bilan)
npm run test:e2e     # ishlab turgan serverga qarshi to'liq API oqimi
```

`test:e2e` har safar tasodifiy Telegram id ishlatadi, shuning uchun uni qayta-qayta
ishga tushirish mumkin. **Faqat sinov bazasiga qarshi ishlating** — u yozadi.

```bash
E2E_BASE_URL=http://localhost:4000 E2E_BOT_TOKEN=<token> npm run test:e2e
```

---

## Ma'lum cheklovlar

- Mashg'ulotni **o'chirish PR'larni qayta hisoblamaydi** — rekord saqlanib qoladi
  (`workoutSetId` `NULL` bo'ladi). Rekordlarni qayta hisoblovchi job hali yo'q.
- Mashg'ulot faqat yakunlanganda serverga yuboriladi; jarayon davomida draft
  brauzer `localStorage`ida turadi. Qurilmalar orasida sinxronlanmaydi.
- Rate limiting yo'q. Ochiq internetga chiqarishdan oldin reverse proxy
  darajasida qo'shing.
- Routine/template (oldindan tayyor dastur) va LB birligida kiritish hali yo'q —
  `User.unit` maydoni bor, lekin UI faqat kg qabul qiladi.
