# GYM Platform — Implementatsiya rejasi (Telegram Mini App)

**Holat:** tasdiqlash kutilmoqda · **Sana:** 2026-09-04
**Asos:** `docs/DECISIONS.md` (5 raundlik tahlil natijasi)

> Bu fayl oldingi rejani (10 bosqichli, allaqachon bajarilgan qurilish) almashtiradi.
> Eski matn Git tarixida qoladi: `git show 00cd629:docs/IMPLEMENTATION_PLAN.md`.

---

## Ishlash usuli

- **Har bosqich = alohida PR/commit** (D: 5-raund E5). Har PR: implementatsiya → testlar →
  migratsiya (kerak bo'lsa) → hujjat yangilanishi.
- Muhim arxitektura/xavfsizlik qarori chiqsa — **keyingi bosqichga o'tmasdan to'xtaymiz** va
  natijani ko'rsatamiz.
- Branch: `claude/grill-with-docs-c0qknm`.
- Har PR yashil CI bilan yopiladi: backend pytest, frontend vitest, bot pytest, lint, type-check, build.

### Har bosqichda majburiy xavfsizlik tekshiruvi (invariant 14)

Bosqich "tugadi" deyilishidan oldin quyidagilar **shu bosqich qamrovida** tekshiriladi:

| # | Tekshiruv |
|---|---|
| 1 | Yangi endpointlarda autentifikatsiya majburiymi |
| 2 | Avtorizatsiya: user faqat o'z ma'lumotini ko'radi; admin yo'llari `role` bilan himoyalangan |
| 3 | Kirish validatsiyasi (Pydantic) + DB cheklovlari (UNIQUE/CHECK/FK) |
| 4 | Rate limit qo'llanganmi (D-152 jadvali) |
| 5 | Audit log kerakmi va yozilyaptimi (D-120) |
| 6 | Maxfiylik: yangi PII bormi, loglarga tushmaydimi (D-146), saqlash muddati belgilanganmi |
| 7 | Xato javoblari ichki tafsilot oshkor qilmaydi |
| 8 | Yangi sir/kalit `.env`da, Git'da emas |
| 9 | Cross-user izolyatsiya testi yozilgan |

### Hujjatlar siyosati

Hujjat kod bilan **bir commitda** o'zgaradi; kelajakdagi holat oldindan qo'lda yozilmaydi.

| Hujjat | Qachon yangilanadi |
|---|---|
| `docs/DATABASE.md` | 2-bosqichda, real sxema bilan birga |
| `docs/API.md` | FastAPI OpenAPI — haqiqat manbai (D-175); endpointlar implementatsiyasi bilan generatsiya qilinadi/yangilanadi |
| `docs/ARCHITECTURE.md` | Real arxitektura o'zgarishi ro'y berganda, o'sha bosqichda |
| `docs/DECISIONS.md` | Qaror o'zgarganda, o'zgarish bilan bir commitda |
| `docs/SECURITY_AUDIT.md` | 10-bosqichda to'liq qayta yoziladi |

---

## Bosqichlar xaritasi

| # | Bosqich | Natija | Bloklovchi ochiq masala |
|---|---|---|---|
| 0 | Cookie/WebView test matritsasi | Auth 4 klientda isbotlangan | O-4 (test qurilmalari) |
| 1 | Auth qayta qurish + rollar + bootstrap admin | Telegram-only kirish | — |
| 2 | Sxema poydevori | Yangi baseline DB | — |
| 3 | Mashqlar API + admin CRUD + tarjima modeli | Katalog to'liq | — |
| 4 | Dasturlar (template + clone + builder API) | Dastur mexanikasi | O-5 (dastur mazmuni) |
| 5 | Mini App UX + offline navbat | **Foydalanuvchi qiymat oladi** | — |
| 6 | Tarix + progress + PR | **Closed beta shu yerdan** | — |
| 7 | Admin panel UI | Boshqaruv | — |
| 8 | Tarjima workflow + AI tarjima + lug'at | uz/ru kontent | O-6, O-8 |
| 9 | Nutrition (food DB, porsiyalar, tarjimalar) | Ovqatlanish moduli | O-7 |
| 10 | Xavfsizlik/maxfiylik audit + o'chirish/eksport | Prodga tayyorlik | O-1, O-2 |
| 11 | Deploy, monitoring, zaxira | Ishga tushirish | O-2, O-3 |

**Birinchi real foydalanuvchilar: 6-bosqichdan keyin** — closed beta, 10–30 kishi, monitoring va
qo'lda qo'llab-quvvatlash bilan. Admin panel hali to'liq bo'lmasa, boshqaruv SQL orqali.

---

## 0-bosqich — Cookie / WebView test matritsasi

**Maqsad:** D-13/D-15 (cookie + silent re-auth) modelini 4 muhitda **empirik isbotlash**.
Taxminga tayanib butun auth qurish — eng qimmat xato bo'lardi.

**Qamrov**
- Minimal test sahifasi: cookie o'rnatadi (`__Host-`, `SameSite=None`, `Partitioned`), qayta
  o'qishga urinadi, `initData` mavjudligini va yangiligini ko'rsatadi, natijani ekranga chiqaradi.
- Backend'da vaqtinchalik `GET/POST /api/v1/_diag/cookie` (faqat `DEBUG=true` da).
- ngrok yoki staging domen orqali HTTPS.

**Test matritsasi**

| Muhit | Cookie o'rnatiladimi | Qayta ochilganda saqlanadimi | `initData` yangilanadimi | `Origin`/`Referer` bormi va ishonchlimi |
|---|---|---|---|---|
| Android Telegram (asosiy) | | | | |
| iOS Telegram | | | | |
| Telegram Desktop | | | | |
| Telegram Web (Chrome) | | | | |
| Telegram Web (Safari) | | | | |
| Telegram Web (Firefox) | | | | |

Oxirgi ustun — D-19 uchun: `Origin`/`Referer` CSRF himoyasining **qo'shimcha** qatlami, shuning
uchun ular yo'q bo'lgan muhit ham qabul qilinadi; muhimi — bu holatni bilib turish va CSRF
tokenli qatlamga tayanish.

**Yetkazma**
- `docs/TELEGRAM_WEBVIEW_MATRIX.md` — to'ldirilgan jadval, skrinshotlar, xulosalar.
- Fizik qurilma bo'lmagan muhitlar uchun: Playwright bilan iframe simulyatsiyasi + hujjatlashtirilgan cheklov (D-23).

**Chiqish mezoni:** har bir muhit uchun "cookie ishlaydi / ishlamaydi, silent re-auth ishlaydi"
javobi yozilgan. Diagnostika endpointi olib tashlangan yoki `DEBUG` ortida qulflangan.

**Xavf:** qurilmalar mavjud bo'lmasligi (O-4). Yumshatish: Android + Desktop + Web'da real test,
iOS uchun hujjatlashtirilgan taxmin va 6-bosqich betasida tekshirish.

---

## 1-bosqich — Auth qayta qurish, rollar, bootstrap admin

**Maqsad:** parolsiz, Telegram-only, cookie sessiyali auth.

**Qamrov**
- `app/core/security.py` — access token 15 daq; refresh token cookie orqali; `hash_token` qoladi.
- `app/models/user.py` — `password_hash` olib tashlanadi; `is_admin` → `role` enum (D-30);
  `RefreshToken`ga `family_id`, `replaced_by_id`, `revoked_reason` qo'shiladi (D-14).
- `app/services/auth_service.py` — `register`/`login` olib tashlanadi; `telegram_webapp_auth`
  yagona kirish nuqtasi; reuse detection va family revoke.
- `app/core/telegram_webapp.py` — freshness 300s (D-16); Redis'da takroriy payload hisoblagichi
  (abuse cheklovi, **bir martalik nonce emas** — D-17); `TELEGRAM_BOT_TOKEN_PREVIOUS` (D-18).
- `app/api/v1/auth.py` — `/telegram-webapp`, `/refresh` (cookie + CSRF), `/logout`.
  `/telegram` (bot uchun) shared secret header bilan himoyalanadi (D-20).
- `app/core/deps.py` — `require_role(...)`; ruxsatsizda 404 (D-112).
- Bootstrap: `BOOTSTRAP_ADMIN_TELEGRAM_IDS` (D-32), faqat ko'tarish, idempotent, audit.
- Frontend: `auth-store` `localStorage`dan RAM'ga o'tadi; `telegram-webapp-gate` silent re-auth
  bilan; `login`/`register` sahifalari olib tashlanadi; `/api/v1/*` proksisi cookie'ni uzatadi.
- Bot: `/link` → "akkauntingiz avtomatik bog'langan" xabari (D: E4); `X-Bot-Secret` yuboradi.

**Testlar**
- `initData` imzosi, muddati, ikki bot token oynasi.
- **Legitim reload testi:** bir xil `initData` bilan qayta auth rad etilmaydi (D-17); takroriy
  payload faqat abuse chegarasidan oshgandagina cheklanadi.
- Cookie yo'q/rad etilgan holatda silent re-auth ishlaydi (D-15, invariant 16).
- Refresh rotation; **reuse detection → butun oila revoke**; logout.
- CSRF: token yo'q/noto'g'ri → rad (asosiy qatlam). `Origin`/`Referer` yo'q bo'lgan muhitda ham
  CSRF tokenli himoya ishlashda davom etadi (D-19).
- Rol: `user` → admin yo'liga 404; `admin` → ruxsat; `super_admin` → rol berish.
- Bootstrap idempotentligi va mavjud adminni tushirmasligi.
- Bot endpointi shared secretsiz → rad.

**Chiqish mezoni:** parol kodi va endpointlari butunlay yo'q; Mini App ochilganda foydalanuvchi
hech qanday forma ko'rmay dashboardga tushadi; cookie yo'q holatda ham (Web) ishlaydi.

---

## 2-bosqich — Sxema poydevori

**Maqsad:** yagona toza Alembic baseline (D-100), `docs/DATABASE.md` yangilanadi.

Qamrov to'rtta ichki qadamga bo'lingan — **bitta bosqich va bitta PR ichida qoladi**, maqsad
faqat migratsiya va sxema ishini boshqariladigan bo'laklarga ajratish. Har substep o'z
testlari bilan yopiladi, keyin keyingisiga o'tiladi.

### 2A — Yadro: DB / auth / user / workout sxemasi
- Eski migratsiya zanjiri o'rniga bitta yangi baseline (`down_revision = None`); eski fayllar
  Git tarixida qoladi, bog'liqlik emas (D-100).
- `NUMERIC` ko'chishi (D-10A) + Pydantic `Decimal`; frontend JSON serializatsiyasi tekshiriladi.
- `users`: `password_hash` olib tashlanadi, `role` enum (D-30), `unit_system`, `profile_completion`.
- `user_profiles`: `date_of_birth` majburiy onboarding maydoni sifatida ishlatiladi; yosh
  hisoblab chiqariladi, saqlanmaydi (D-52).
- `RefreshToken`: `family_id`, `replaced_by_id`, `revoked_reason` (D-14).
- `workout_session_exercises` kiritiladi; `workout_sets.workout_session_exercise_id` (D-103);
  `client_event_id` + `UNIQUE(session_id, client_event_id)` (D-61); `entered_value`/`entered_unit`
  (D-10B); `set_type`; `rpe`; `distance_m`; `deleted_at`.
- `workout_sessions`: `source_type`, ikki nullable FK + CHECK (D-104), `last_activity_at`,
  `abandoned` status, bitta faol sessiya uchun qisman unique indeks (D-66).
- `personal_records` log modeliga (D-106) + `estimated_1rm` (D-107).
- `body_measurements` `UNIQUE(user_id, date)` (D-10D).

### 2B — Mashqlar: media, tarjima, importer
- `exercise_tracking_type` + `tracking_type_source` (D-101); `workout_sets` CHECK'lari (D-102).
- `exercises`: `media_key`, `media_provider`, `media_license_status`, `license_note`,
  `license_url`; `gif_url`/`image_url` olib tashlanadi (D-80, D-83).
- `exercise_translations` status maydonlari (D-91).
- Importer yangilanadi: `media_key`, `tracking_type`, `source='imported'`, maydon override
  bayroqlari (D-117).

### 2C — Dasturlar sxemasi
- `program_templates`, `program_template_translations`, `program_template_days`,
  `program_template_day_exercises`, `program_template_set_targets` (D-70..D-72, D-77, D-95).
- `user_programs`, `user_program_days`, `user_program_day_exercises`, `user_program_set_targets`
  (D-73, D-74).
- Guruhlash ustunlari: `group_key`, `group_type`, `group_order`, `group_rounds` (D-7A).

### 2D — Nutrition, audit va yordamchi sxema
- `food_item_translations`, `food_item_servings` (D-94, D-133).
- `translation_glossary` (D-97).
- `audit_logs` append-only (DB grant darajasida, D-122) + diff maydoni (D-121).

**Testlar**
- `alembic upgrade head` toza bazada; import 1323 mashqni yozadi.
- Har CHECK constraint uchun buzuvchi holat testi.
- `client_event_id` dublikati yangi qator yaratmaydi.
- Bitta faol sessiya indeksi ikkinchisini rad etadi.
- `Decimal` API orqali to'g'ri serializatsiya bo'ladi.
- `audit_logs`ga UPDATE/DELETE urinishi DB darajasida rad etiladi.

**Chiqish mezoni:** yangi sxema o'rnatiladi, ma'lumot importlanadi, barcha mavjud testlar
yangilangan holda yashil. `docs/DATABASE.md` haqiqatga mos.

---

## 3-bosqich — Mashqlar API + admin CRUD + tarjima modeli

**Qamrov**
- `GET /exercises` — `snake_case` parametrlar (D-172), faqat autentifikatsiyalangan (D-155),
  ro'yxatda **faqat thumbnail** (D-82), tartiblash (D-11A), `tracking_type` qaytadi.
- `GET /exercises/{id}` — thumb + full media, tarjima statusi bilan (D-92).
- `ExerciseMediaProvider` abstraksiyasi (D-81) + `BLOCK_UNVERIFIED_MEDIA` (D-84).
- Admin: `POST/PATCH /admin/exercises`, `PATCH .../deactivate`, lookup CRUD (D-118),
  maydon override (D-117), slug generatsiyasi (D-119), audit (D-120, diff bilan D-121).
- Tarjima o'qish/yozish API'si; fallback zanjiri (D-93).
- CSV import (dry-run bilan, D-11L) — tarjimalar uchun.

**Testlar:** filtrlash/sahifalash; ruxsatsiz admin → 404; override importda saqlanadi;
fallback zanjiri; `BLOCK_UNVERIFIED_MEDIA` placeholder qaytaradi; audit diff yoziladi.

---

## 4-bosqich — Dasturlar

**Qamrov**
- Template CRUD + versiyalash (`draft → published → archived`, avtomatik yangi versiya, D-77).
- Publish validatsiyasi (D-11G) — alohida, testlanadigan servis.
- `POST /programs/{id}/start` → to'liq klon (D-73); bitta faol dastur (D-74).
- `user_program` o'qish/tahrir API'si; kun holatlari; erkin jadval (D-75).
- Konstruktor yordamchi endpointlari: hafta/kun klonlash, `3 × 8–12` set generatsiyasi (D-11C, D-11D).
- 6 ta boshlang'ich dastur seed skripti (mazmun O-5 dan keladi; kelmasa — struktura tayyor,
  mazmun placeholder va aniq belgilangan TODO bilan).

**Testlar:** klon originaldan mustaqilligi; published versiya o'zgarmasligi; validatsiya
qoidalarining har biri; ikkinchi dastur boshlanganda birinchisi `paused`.

---

## 5-bosqich — Mini App UX + offline navbat

**Qamrov**
- 5 tabli navigatsiya (D-50), bosh sahifa "bugun nima qilish kerak" (D-51).
- Onboarding (D-52), til avtomatik aniqlash (D-53).
- Telegram integratsiyasi: `themeParams`, `BackButton`, `expand`, `disableVerticalSwipes`,
  haptics, `MainButton` (D-54).
- Sessiya ekrani: set kiritish, rest timer (D-63), tahrir/o'chirish/skip/almashtirish/qo'shish
  (D-65), "davom ettirasizmi?" (D-68).
- Offline navbat: optimistic UI, `client_event_id`, avtomatik sync, backoff+jitter (D-60, D-154),
  `sets/batch` endpointi (D-151).
- Birlik tanlovi kg/lb (D-10B, D-10C).

**Testlar:** Vitest — navbat mantiqi (takror yuborish, tartib, xato holati); Playwright —
dastur boshlash → sessiya → setlar → tugatish; oflayn simulyatsiyasi.

**Chiqish mezoni:** internet uzilib-ulanadigan sharoitda trening yozuvi yo'qolmaydi.

---

## 6-bosqich — Tarix, progress, personal records

**Qamrov**
- `GET /workout-sessions` (kursor sahifalash, D-173), sessiya detali, mashq bo'yicha tarix.
- PR: har set yozilganda idempotent hisoblash (D-108), qoidalar (D-109), `estimated_1rm` (D-107).
- **Qayta hisoblash servisi** — tahrir/o'chirishdan keyin PR va agregatlarni manba setlardan
  qayta quradi (D-106, D-69).
- 24 soatlik tahrir oynasi (D-69); ARQ orqali `abandoned` belgilash (D-67).
- Progress: SQL darajasida filtrlash (hozirgi Python filtri o'rniga), vazn/hajm/chastota trendlari.
- Mini App: tarix ro'yxati, sessiya detali, progress grafiklari, PR ko'rsatkichlari.

**Testlar:** PR sindirilishi va tiklanishi; set o'chirilganda oldingi PR qaytishi; 24 soatdan
keyin tahrir rad etilishi; kursor sahifalashning barqarorligi.

**Majburiy qabul testi (D-69, D-106):** tugallangan sessiyada set tahrirlanadi → PR qayta
hisoblanadi → eskirgan PR `superseded` holatiga o'tadi → yangi PR holati to'g'ri shakllanadi.
Qayta hisoblash **idempotent**: ikki marta ishga tushirilganda natija o'zgarmaydi; joriy PR
har doim `(user_id, exercise_id, record_type)` bo'yicha eng oxirgi `superseded` bo'lmagan yozuv.

**➡️ Shu bosqichdan keyin closed beta (10–30 foydalanuvchi).**

---

## 7-bosqich — Admin panel UI

**Qamrov**
- `/admin` lazy chunk (D-111); Telegram Login Widget bilan desktop kirish (D-110).
- Dashboard (D-113) + Redis kesh (D-114) + `APP_TIMEZONE` (D-115).
- Mashqlar ro'yxati: filtrlar va tartiblash (D: Q12.1/Q12.2), ommaviy amallar tasdiq bilan (Q12.3).
- Mashq tahrir formasi; lookup boshqaruvi; media va litsenziya boshqaruvi (D-83, D-87).
- Dastur konstruktori (D-11C, D-11D, D-11E, D-11F).
- Foydalanuvchilar: qidiruv/filtr, amallar (D-11J), ma'lumot ko'rish audit bilan (D-11I).
- Rollar (D-31..D-36).
- Audit log UI + CSV (D-124).
- Import/eksport oqimi dry-run bilan (D-11L, D-11M).
- Admin xavfsizligi: qisqa sessiya (access 10 daq / refresh 24 soat), destruktiv amallar uchun
  tasdiq + sabab, alohida rate limit (D-152).

---

## 8-bosqich — Tarjima workflow + AI tarjima

**Qamrov**
- Review UI: EN|UZ|RU yonma-yon + jadval rejimi; bulk approve ≤50, audit (D-11H).
- `translation_glossary` CRUD + promptga avtomatik qo'shish (D-97).
- AI tarjima: bitta/ommaviy (D-11O), narx va token bahosi (D-11P), ARQ fon ishi va progress (D-11R).
- `AI_MONTHLY_BUDGET_USD` limiti va bloklash.
- `source_content_hash` → EN o'zgarganda `stale` (D-91).
- Navbat tartibi (D-96).

**Bog'liqlik:** O-8 (OpenAI kaliti) va O-6 (lug'at). Kalit bo'lmasa: workflow, UI, navbat va
qo'lda tarjima to'liq ishlaydi; AI tugmasi `503 AI_NOT_CONFIGURED` beradi (mavjud pattern).

---

## 9-bosqich — Nutrition

**Qamrov**
- USDA import skripti + mahalliy taomlar seedi, `source`/`source_reference` bilan (D-130, D-131).
- `food_item_servings` (D-133) va porsiya asosida hisoblash.
- `food_item_translations` + review workflow (D-94).
- Foydalanuvchi mahsuloti shaxsiy → admin tasdiqlasa umumiy (D-132).
- Admin: ovqat CRUD, tasdiqlash navbati.
- Mini App: ovqat qidiruvi, porsiya tanlash, kunlik xulosa.

**Bog'liqlik:** O-7 (mahalliy ovqat ma'lumotlari manbasi).

---

## 10-bosqich — Xavfsizlik va maxfiylik: yakuniy audit

> Bu **birinchi** xavfsizlik ishi emas — har bosqichda tekshiruv o'tgan (invariant 14).
> Bu yakuniy hardening va hujjatlashtirish.

**Qamrov**
- Akkaunt o'chirish: 30 kunlik grace → anonimlashtirish (D-142, D-143), ARQ ishi.
- Ma'lumot eksporti JSON+CSV, bot orqali yetkazish (D-144).
- Saqlash muddatlari ishlari: AI suhbatlari 90 kun, rasmlar 30 kun, faol bo'lmagan akkauntlar
  24 oy, audit 1 yil (D-145) — konfiguratsiya bilan.
- Log tozaligi auditi (D-146) — barcha log chaqiruvlari ko'rib chiqiladi.
- Maxfiylik siyosati va shartlar sahifalari (D-147, texnik qoralama).
- AI xavfsizlik cheklovlari promptlarda va javob validatsiyasida (D-127).
- `docs/SECURITY_AUDIT.md` to'liq qayta yoziladi.
- Yakuniy tekshiruv: cross-user izolyatsiya, rate limit fail-open/closed (D-153), CSRF,
  cookie atributlari, sirlarning Git'da yo'qligi (`git log -p` bo'yicha).

---

## 11-bosqich — Deploy, monitoring, zaxira

**Qamrov**
- `docker-compose.prod.yml`, reverse proxy/Cloudflare bilan ishlash (D-162).
- Staging + production muhitlari, alohida botlar (D-163).
- GitHub Actions: CI har PR'da; staging avtomatik; production qo'lda tasdiq bilan (D-164).
- Deploy pipeline: `backup → migration → backend → frontend → bot → health check` (D-169).
- Zaxira: kunlik dump + retention + **stagingga restore testi** (D-165).
- Monitoring: Sentry, uptime, DB/Redis metrikalari, disk/RAM ogohlantirishlari, AI xarajat (D-166).
- Bot webhookka o'tadi (D-168).
- `docs/RUNBOOK.md`: deploy, rollback, restore, sir almashtirish, incident tartibi.

**Bog'liqlik:** O-2 (lokalizatsiya), O-3 (domen/hosting).

---

## Nima qachon bloklanadi

| Ochiq masala | Bloklaydi | Bloklamaydi |
|---|---|---|
| O-1 media litsenziyasi | Commercial production release | Development, closed beta |
| O-2 ma'lumot lokalizatsiyasi | Production hosting tanlash (11) | 0–10 bosqichlar |
| O-3 domen/hosting | 11-bosqich | 0–10 bosqichlar |
| O-4 test qurilmalari | 0-bosqichning to'liqligi | Qolgan bosqichlar (cheklov hujjatlashtiriladi) |
| O-5 dastur mazmuni | 4-bosqich **mazmuni** | 4-bosqich **mexanikasi** |
| O-6 atamalar lug'ati | 8-bosqich sifati | Workflow qurilishi |
| O-7 ovqat ma'lumotlari | 9-bosqich mazmuni | 9-bosqich mexanikasi |
| O-8 OpenAI kaliti | AI tarjima ishga tushishi, AI murabbiy | Qolgan hamma narsa |

---

## Keyingi qadam

Ushbu reja va `docs/DECISIONS.md` tasdiqlangandan keyin **0-bosqich**dan boshlanadi.
0-bosqichdan oldin O-4 (qaysi Telegram klientlari test uchun mavjud) javobi kerak.
