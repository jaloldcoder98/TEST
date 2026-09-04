# GYM Platform — Qabul qilingan qarorlar (Decision Log)

**Holat:** tasdiqlangan · **Sana:** 2026-09-04 · **Manba:** mahsulot egasi bilan 5 raundlik
tahlil (product, UX, arxitektura, DB, auth, xavfsizlik, biznes qoidalari).

Bu hujjat — loyihaning yagona haqiqat manbai. Kod bilan hujjat orasida ziddiyat bo'lsa, avval
shu hujjatga qaraladi; qaror o'zgarsa, hujjat **o'sha o'zgarish bilan bir commitda** yangilanadi.

Har bir qaror `D-NN` identifikatoriga ega. Kodda muhim joylarda `# D-14` kabi havola qoldiriladi.

---

## 0. Kontekst

Loyiha noldan boshlanmaydi. Mavjud holat:

| Komponent | Holati |
|---|---|
| Backend | FastAPI, SQLAlchemy 2 (async), Postgres, Redis, ARQ, Alembic, 50 test |
| Frontend | Next.js 15 App Router, TS, Tailwind, next-intl (uz/ru/en), TanStack Query, Zustand |
| Bot | aiogram 3, backend API klienti, 40 test; `/start` → "Open App" Web App tugmasi |
| Mashqlar | `ExerciseGymGifsDB` importi: 1323 mashq, 19 mushak, 12 jihoz, 7 tana qismi, 4 kategoriya |
| Mini App auth | `POST /auth/telegram-webapp`, `initData` HMAC server tomonda tekshiriladi |
| Yo'q | Admin panel, dasturlar (programs), trening tarixi API, web profil, offline navbat |

Mahsulot **Telegram Mini App markazli B2C fitnes platformasi**ga qayta yo'naltiriladi.

**Muhim shart:** productionda real foydalanuvchi yo'q → sxema va auth toza qayta qurilishi mumkin.

---

## 1. Mahsulot va qamrov

| ID | Qaror | Sabab |
|---|---|---|
| **D-01** | Mavjud kodbaza davom ettiriladi, noldan yozilmaydi | Auth, import, set logging allaqachon ishlaydi |
| **D-02** | Telegram Mini App — yagona asosiy mahsulot | Marketing landing keyinroq qo'shilishi mumkin |
| **D-03** | Brauzer uchun alohida email/parol mahsuloti **yo'q** | Telegram identity yetarli |
| **D-04** | Botning matnli buyruqlari saqlanadi, lekin asosiy UX emas | Bosqichma-bosqich qisqartirish mumkin |
| **D-05** | Nutrition qamrovda qoladi | Mavjud kod tashlab yuborilmaydi |
| **D-06** | AI (murabbiy, workout generator, food analysis) roadmapda qoladi, `OPENAI_API_KEY` bo'lmasa **disabled** holatda | AI asosiy workout oqimiga qattiq bog'lanmaydi |
| **D-07** | MVPda pullik obuna yo'q; entitlement uchun `can(user, "feature")` seam qoldiriladi | Telegram Stars keyin qo'shiladi |
| **D-08** | B2C self-service; trainer-client modeli keyingi bosqich | Rol arxitekturasi `trainer` uchun ochiq |

---

## 2. Autentifikatsiya va sessiya

| ID | Qaror |
|---|---|
| **D-10** | **Telegram `initData` — yagona login usuli.** Email/parol butunlay olib tashlanadi (`/auth/register`, `/auth/login`, `users.password_hash`, parol orqali `link-telegram`) |
| **D-11** | `telegram_id` — asosiy identity. Akkaunt `telegram_id` bo'yicha idempotent provizyalanadi |
| **D-12** | **Access token** — faqat JS xotirasida (RAM), 10–15 daqiqa. Hech qachon `localStorage`/`sessionStorage`/`CloudStorage`da saqlanmaydi |
| **D-13** | **Refresh token** — `__Host-` prefiksli, `httpOnly; Secure; SameSite=None; Partitioned; Path=/` cookie. `Domain` atributi ishlatilmaydi |
| **D-14** | Refresh sessiya muddati **7 kun**; rotation + **reuse detection** + **family revoke** |
| **D-15** | **Cookie — haqiqat manbai emas, optimizatsiya.** Cookie yo'q/rad etilgan bo'lsa → yangi `initData` bilan **silent re-auth**. Foydalanuvchi hech qachon login formasini ko'rmaydi |
| **D-16** | `initData` freshness oynasi — **300 soniya** (24 soat emas) |
| **D-17** | `initData` **bir marta ishlatiladi**: hash Redis'da 5 daqiqaga saqlanadi, takroriy kelsa rad etiladi. Legitim reload oqimlari integratsion test bilan qoplanadi |
| **D-18** | Bot token rotatsiyasi uchun `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_TOKEN_PREVIOUS` — o'tish davrida ikkalasi ham qabul qilinadi |
| **D-19** | **CSRF — uch qatlam:** (1) cookie faqat `POST /auth/refresh`da ishlatiladi, qolgan hamma joyda `Authorization: Bearer`; (2) double-submit CSRF token (`X-CSRF-Token`); (3) `Origin`/`Referer` validatsiyasi |
| **D-20** | Bot → backend chaqiruvlari: **shared secret header** (`X-Bot-Secret`, constant-time solishtirish) + imkon bo'lsa internal tarmoq cheklovi. `telegram_id`ni request body'dan olib login qilish **taqiqlanadi** |
| **D-21** | `initData` bo'lmagan brauzer: "Bu ilova Telegram ichida ishlaydi" sahifasi + botga tugma |

### Telegram muhitlari — tasdiqlangan fakt

| Muhit | Yuklanishi | Cookie |
|---|---|---|
| iOS / Android ilova | Native WebView, top-level hujjat | Birinchi tomon ✅ |
| Telegram Desktop | Native WebView | Birinchi tomon ✅ |
| Telegram Web (`web.telegram.org`) | **`<iframe>`** | Uchinchi tomon ⚠️ Safari bloklaydi, Firefox partitsiyalaydi, Chrome `Partitioned` bilan ishlaydi |

Bundan tashqari iOS WKWebView'da `localStorage`/cookie tasodifiy o'chishi — hujjatlashtirilgan,
takrorlanmaydigan muammo. **D-15 aynan shuning uchun majburiy.**

| ID | Qaror |
|---|---|
| **D-22** | Telegram Web rasman qo'llab-quvvatlanadi; "ilovada oching" cheklovi qo'yilmaydi |
| **D-23** | Test matritsasi ustuvorligi: **Android (asosiy)** → iOS → Desktop → Web. Fizik qurilma bo'lmasa: avtomatlashtirilgan brauzer testi + hujjatlashtirilgan cheklov |

---

## 3. Rollar va admin

| ID | Qaror |
|---|---|
| **D-30** | `users.is_admin` (boolean) → `users.role` enum: `user \| trainer \| admin \| super_admin`. `trainer` band qilinadi, MVPda ishlatilmaydi |
| **D-31** | Faqat `super_admin` rol bera/olib qo'ya oladi. `admin` faqat kontent boshqaradi |
| **D-32** | Birinchi admin: `.env` → `BOOTSTRAP_ADMIN_TELEGRAM_IDS`. Mexanizm **faqat ko'taradi, hech qachon tushirmaydi**, idempotent, audit logga yoziladi |
| **D-33** | `super_admin` boshqa `super_admin`ni tushira olmaydi |
| **D-34** | Oxirgi `super_admin`ni tushirish/o'chirish DB va ilova darajasida bloklanadi |
| **D-35** | O'z-o'zini tushirish (self-demotion) taqiqlanadi |
| **D-36** | Rol o'zgarishida majburiy `reason` matni, audit logga yoziladi |
| **D-37** | MVPda alohida `translator` roli yo'q; RBAC arxitekturasi uni keyin qo'shishga ochiq |

---

## 4. Biznes model va multi-tenancy

| ID | Qaror |
|---|---|
| **D-40** | MVPda `organization_id` **qo'shilmaydi** — o'qilmaydigan nullable ustun o'lik yuk va yolg'on xotirjamlik beradi |
| **D-41** | O'rniga bepul turadigan 5 ta seam: (1) barcha scoped so'rovlar bitta `scoped()` yordamchisidan o'tadi; (2) `slug` unikalligi kelajakda `(organization_id, slug)` bo'lishi hujjatlashtiriladi; (3) UUID PK (allaqachon); (4) kontent va user ma'lumoti ajratiladi; (5) `can(user, feature)` entitlement seam |
| **D-42** | Kelajakdagi migratsiya: `organizations` → `users.organization_id` backfill → `organization_members(user_id, org_id, role)` → kontent jadvallariga `organization_id NULL = platforma-global` |

---

## 5. Mini App UX

| ID | Qaror |
|---|---|
| **D-50** | 5 ta pastki tab: **Bosh sahifa · Mashqlar · Trening · Ovqatlanish · Profil**. Progress alohida tab emas: bosh sahifada qisqa summary, batafsili Profil/Trening ichida |
| **D-51** | Bosh sahifa "bugun nima qilish kerak?" savoliga darhol javob beradi |
| **D-52** | Onboarding majburiy maydonlari: til, yosh, bo'y, vazn, maqsad, tajriba darajasi, haftalik trening kunlari. **Jins — ixtiyoriy.** Skip mumkin, `profile_completion` holati saqlanadi |
| **D-53** | Til Telegram `language_code`dan avtomatik: `uz*`→uz, `ru*`→ru, qolgani→en. Profil→Sozlamalarda qo'lda o'zgartiriladi. Fallback: `en` |
| **D-54** | Telegram integratsiyasi: `themeParams` (majburiy), `BackButton` (majburiy), `expand` (majburiy), `disableVerticalSwipes` (sessiya paytida majburiy), haptic feedback, `MainButton` (kerakli ekranlarda). `CloudStorage` — MVPda yo'q |

---

## 6. Trening sessiyasi

| ID | Qaror |
|---|---|
| **D-60** | **Optimistic UI + lokal navbat.** Set: UI'da darhol → lokal navbat → internet bo'lsa yuboriladi → qaytganda avtomatik sync |
| **D-61** | **Idempotentlik:** har set `client_event_id` (UUID) bilan. `UNIQUE(workout_session_id, client_event_id)`. Takror yuborilsa server dublikat yaratmaydi, mavjudini qaytaradi |
| **D-62** | To'liq offline-first (IndexedDB) MVPda kerak emas, lekin kengaytirishga ochiq |
| **D-63** | Rest timer set tugagach avtomatik. Default: compound `120s`, izolyatsiya `90s`, isinish `60s`. Foydalanuvchi o'zgartira oladi; dastur o'z `rest_seconds`ini belgilashi mumkin |
| **D-64** | Timer uchun Telegram bildirishnomasiga bog'lanilmaydi (Mini App yopiq bo'lsa ishlamaydi). Server-side reminder keyingi bosqich |
| **D-65** | Sessiya ichida ruxsat: set tahriri, set o'chirish, mashqni skip qilish, mashqni almashtirish, rejadan tashqari mashq qo'shish — **faqat sessiya snapshotiga ta'sir qiladi** |
| **D-66** | Bir userda bir vaqtda **bitta** faol sessiya. DB darajasida qisman unique indeks |
| **D-67** | Sessiya statuslari: `in_progress · paused · completed · abandoned · cancelled`. `cancelled` = user bekor qildi, `abandoned` = tizim 24 soatdan keyin yopdi |
| **D-68** | Ilova qayta ochilganda tugallanmagan sessiya uchun "Davom ettirasizmi?" |
| **D-69** | Tugallangan sessiyani tahrirlash — **24 soat ichida**, keyin read-only. Har tahrirdan keyin agregatlar va PR'lar qayta hisoblanadi |

---

## 7. Dasturlar (Programs)

| ID | Qaror |
|---|---|
| **D-70** | Ikki alohida daraxt: `program_template*` (admin) va `user_program*` (foydalanuvchi nusxasi) |
| **D-71** | Ierarxiya **yassi**: `program → days (week_no, day_no)`. Alohida `weeks` jadvali yo'q |
| **D-72** | Target'lar — **har set alohida qator** (`*_set_targets`), `set_type`: `warmup \| working \| dropset \| amrap`. Isinish setini ishchi setdan ajratish uchun majburiy |
| **D-73** | Dastur boshlanganda **to'liq clone** qilinadi. Admin originalni o'zgartirsa, boshlangan dastur o'zgarmaydi |
| **D-74** | Bitta faol structured dastur + istalgancha standalone workout. Yangi dastur boshlanganda eskisi default `paused` |
| **D-75** | Jadval **erkin**: "1-hafta 2-kun" istalgan kalendar kunida bajariladi. O'tkazib yuborilgan kun progressni bloklamaydi |
| **D-76** | MVPda progression engine **yo'q**. Target'lar qat'iy (reps range, target weight, RPE, duration, rest); ishchi vaznni foydalanuvchi kiritadi |
| **D-77** | Versioning: `draft → published → archived`. Published versiya **o'zgarmas**; tahrir qilinganda avtomatik yangi `draft` versiya yaratiladi. v1 published bo'lganda v2 draft mavjud bo'lishi mumkin |
| **D-78** | Archived dastur kutubxonada ko'rinmaydi, davom etayotganlar tugatadi. Hard delete faqat hech kim boshlamagan `draft` uchun |
| **D-79** | Ishga tushish dasturlari: Beginner Full Body 3d, Beginner Full Body 4d, Hypertrophy 4d, Upper/Lower 4d, PPL 5–6d, General Fitness 3d |
| **D-7A** | Guruhlash: `group_key`, `group_type` (`superset \| giant_set \| circuit \| dropset_chain`), `group_order`, `group_rounds`. Alohida `exercise_groups` jadvali MVPda yo'q |

---

## 8. Media

| ID | Qaror |
|---|---|
| **D-80** | `exercises.gif_url`/`image_url` olib tashlanadi → `media_key` + `media_provider` (`jsdelivr_egg \| s3 \| local`) |
| **D-81** | `ExerciseMediaProvider` abstraksiyasi; frontend hech qachon URL qurmaydi, API to'liq URL qaytaradi |
| **D-82** | Ro'yxatda **faqat thumbnail** (WebP), full GIF faqat detal/sessiyada. Lazy loading + sahifalash |
| **D-83** | `media_license_status`: `unverified \| licensed \| own \| replaced` + `license_note`, `license_url`. O'zgarishlar audit qilinadi |
| **D-84** | `.env` → `BLOCK_UNVERIFIED_MEDIA`. `true` bo'lganda `unverified` media o'rniga placeholder ko'rsatiladi. Production релизdan oldin yoqiladi |
| **D-85** | Litsenziyasi noaniq media bilan **commercial production release qilinmaydi** — bu ochiq masala (§17) |
| **D-86** | Media health check (buzilgan URL) — ARQ arxitekturasi tayyorlanadi, birinchi relizda majburiy emas |
| **D-87** | Admin fayl yuklash — keyingi bosqich. MVPda `media_key`/`provider` qo'lda almashtiriladi |

---

## 9. Ko'p tillilik (i18n)

| ID | Qaror |
|---|---|
| **D-90** | UI uz/ru/en (mavjud). Mashq kontenti: AI tarjima + **majburiy inson tekshiruvi** |
| **D-91** | `exercise_translations` kengaytiriladi: `status` (`missing → machine → needs_review → approved \| rejected`, EN o'zgarsa → `stale`), `translated_by`, `ai_model`, `reviewed_by`, `reviewed_at`, `source_language`, `source_content_hash`. `is_machine_translated` olib tashlanadi |
| **D-92** | **Ko'rsatish qoidasi (gibrid):** `name` — machine tarjima bo'lsa ham ko'rsatiladi; `instructions` — faqat `approved` bo'lsa, aks holda EN fallback. Backend statusni javobda qaytaradi |
| **D-93** | Fallback zanjiri: so'ralgan til → `en` → slug'dan hosil qilingan nom |
| **D-94** | `food_items` ustunlari (`name_ru`, `name_uz`) → `food_item_translations` jadvaliga o'tkaziladi. Mashq bilan **bir xil workflow** |
| **D-95** | `program_template_translations` — uz/ru/en, `name` + `description`, bir xil status workflow |
| **D-96** | Tarjima navbati: (1) dasturlarda ishlatiladigan mashqlar, (2) userlar eng ko'p ishlatadigan, (3) mushak guruhi bo'yicha asosiylari |
| **D-97** | **`translation_glossary(term_en, term_uz, term_ru, notes)`** — 50–100 fitnes atamasi, har AI so'roviga promptga qo'shiladi. Izchillik uchun majburiy |
| **D-98** | AI tarjima **hech qachon avtomatik `approved` bo'lmaydi** — doim `needs_review` |

---

## 10. Ma'lumotlar bazasi

| ID | Qaror |
|---|---|
| **D-100** | **Toza baseline migratsiya.** Eski migratsiya zanjiri almashtiriladi, ma'lumot qayta import qilinadi. Migratsiya tarixi Git'da qoladi; production sxemasi qo'lda o'zgartirilmaydi |
| **D-101** | `exercise_tracking_type`: `strength \| bodyweight \| cardio \| timed` + `tracking_type_source` (`derived \| admin_override`). Importda avtomatik aniqlanadi: `cardio`→cardio, `stretching`→timed, `bodyweight` jihoz→bodyweight, qolgani→strength. `plyometrics`→bodyweight |
| **D-102** | `workout_sets` DB CHECK: strength→weight+reps; bodyweight→reps; cardio→duration yoki distance; timed→duration |
| **D-103** | **`workout_session_exercises`** kiritiladi — sessiya boshlanganda reja + target'lar snapshot qilinadi. `workout_sets.workout_exercise_id` → **`workout_session_exercise_id`** |
| **D-104** | `workout_sessions` manbasi: `source_type` + `workout_id` / `user_program_day_id` (nullable FK + CHECK; polimorf ID emas) |
| **D-105** | To'rt tushuncha aniq ajratiladi: `program_template` (admin) · `user_program` (klon) · `workout` (userning qayta ishlatiladigan shaxsiy rejasi) · `workout_session` (bajarilgan real trening). **Tarix faqat `workout_session` orqali** |
| **D-106** | `personal_records` — **rekordlar tarixi (log)**, joyida yangilash emas. `superseded_at`, kontekst (`reps`, `weight_kg`), `UNIQUE(user, exercise, type, workout_set_id)`. Manba setlardan **qayta hisoblanadigan** bo'lishi shart |
| **D-107** | Rekord turlari: `max_weight`, `max_reps`, `max_volume`, **`estimated_1rm`** (Epley: `w × (1 + reps/30)`), kodda va UI'da "taxminiy" deb belgilanadi |
| **D-108** | PR **har set yozilganda** hisoblanadi (sync'dan keyin). Idempotent. Offline holatda UI PR va'da qilmaydi |
| **D-109** | PR qoidalari: isinish setlari hisobga olinmaydi; `weight_kg IS NULL` bo'lsa `max_weight` hisoblanmaydi |
| **D-10A** | O'lchov qiymatlari `Float` → **`NUMERIC`**: vazn, hajm, ozuqa, tana o'lchovlari, masofa. Butun/mantiqiy/matn maydonlar o'z turida qoladi. API'da `Decimal`; frontend JSON serializatsiyasi tekshiriladi |
| **D-10B** | Kanonik birlik — **kg**. Qo'shimcha: `entered_value` + `entered_unit` (`kg \| lb`) saqlanadi → foydalanuvchi kiritgan qiymat aynan qaytariladi (round-trip muammosi yo'q) |
| **D-10C** | Yaxlitlash: vazn saqlash 2 kasr, ko'rsatish 1 kasr; `lb = kg × 2.20462262185`; hajm butun; bo'y `NUMERIC(5,1)`. `user_profiles.unit_system: metric \| imperial` |
| **D-10D** | `body_measurements` — `UNIQUE(user_id, date)` qo'shiladi (hozir poyga sharti bor) |
| **D-10E** | Biznes qoidalari iloji boricha DB darajasida: `UNIQUE`, `CHECK`, `FK`, qisman unique indeks. Faqat Python validatsiyasiga tashlanmaydi |

---

## 11. Admin panel

| ID | Qaror |
|---|---|
| **D-110** | Bitta Next.js ilova, **ikki kirish yo'li**: Mini App ichidan `/admin` va desktop brauzerdan Telegram Login Widget. Ikkalasida ham identity server tomonda HMAC bilan tekshiriladi |
| **D-111** | Admin bundle — alohida lazy chunk |
| **D-112** | Admin huquqi yo'q bo'lsa **404** (403 emas) — admin yo'lining borligi oshkor qilinmaydi |
| **D-113** | Dashboard: DAU/WAU/MAU, bugungi yangi userlar, bugungi tugallangan sessiyalar, aktiv dasturlar, top-10 mashq, uz/ru tarjima qamrovi %, tekshirilmagan media soni, AI so'rov va xarajati, 5xx, onboarding tugallanmaganlar % |
| **D-114** | Statistika: jonli SQL + Redis 5 daqiqalik kesh. `admin_daily_stats` rollup keyin |
| **D-115** | `.env` → **`APP_TIMEZONE=Asia/Tashkent`**. Server/DB UTC'da, kunlik agregatlar Toshkent vaqti bo'yicha |
| **D-116** | Admin mashqda hamma narsani tahrirlaydi (taksonomiya, tracking_type, media, litsenziya, `is_active`, EN nom va yo'riqnoma, `sort_order`, `featured`). Har o'zgarish audit logga |
| **D-117** | **Maydon darajasidagi override:** admin qo'lda o'zgartirgan maydon qayta importda ustidan yozilmaydi |
| **D-118** | Admin yangi lookup (mushak/tana qismi/jihoz/kategoriya) qo'sha oladi; hard delete yo'q, faqat `is_active=false` |
| **D-119** | Slug nomdan avtomatik, admin qo'lda tuzata oladi; `UNIQUE(slug)`, to'qnashuvda avtomatik suffiks |
| **D-11A** | Katalog tartibi: `is_featured` → ishlatilish chastotasi → nom; admin `sort_order` bilan ustidan chiqadi |
| **D-11B** | Dublikat mashq uchun merge vositasi MVPda yo'q — faqat `is_active=false` |
| **D-11C** | Dastur konstruktori: 1 hafta yoziladi → "N haftaga nusxala" → kerakli haftalar qo'lda tuzatiladi. Sxema o'zgarmaydi, bu UI vositasi |
| **D-11D** | Konstruktor vositalari: `3 × 8–12` preset, mashq avtokompliti, kun/hafta klonlash, drag&drop tartiblash, set tartiblash, ommaviy set yaratish, set turlari, rest, superset/circuit |
| **D-11E** | Admin mavjud dasturdan klon qilib yangisini boshlay oladi |
| **D-11F** | Nashrdan oldin preview + admin o'ziga test sifatida boshlashi. Test sessiyalar `is_test=true` va analitika/PR statistikasiga kirmaydi |
| **D-11G** | Publish validatsiyasi: bo'sh kun yo'q · har mashqda ≥1 set · `is_active=false` mashq yo'q · `days_per_week` mos · barcha majburiy tillarda nom · target'lar valid · dublikat tartib yo'q · guruh konfiguratsiyasi valid · target'lar `tracking_type`ga mos |
| **D-11H** | Tarjima review UI: asosiy — EN\|UZ\|RU yonma-yon; qo'shimcha — jadval ko'rinishida ommaviy. Bulk approve **maksimal 50 ta**, audit logga |
| **D-11I** | Admin foydalanuvchi ma'lumotini (sessiyalar, setlar, progress, ovqat kunligi) **ko'ra oladi**, lekin **har ko'rish audit qilinadi** (admin, target user, vaqt, sabab) |
| **D-11J** | Admin amallari: deactivate, ban/unban, rol o'zgartirish, til o'zgartirish, akkaunt o'chirish, GDPR eksport. **Impersonation MVPda yo'q** |
| **D-11K** | Ban/deactivate → barcha sessiyalar va refresh token oilasi darhol revoke |
| **D-11L** | Import: CSV (tarjima/ma'lumot, birinchi prioritet), JSON (dasturlar), XLSX keyin. Oqim: `upload → validate → dry-run → diff hisoboti → tasdiqlash → apply`. **Dry-run majburiy** |
| **D-11M** | Eksport MVPda: GDPR user ma'lumoti, tarjimalar, dasturlar. To'liq DB zaxirasi — admin UI orqali emas, infra qatlamida |
| **D-11N** | `ExerciseGymGifsDB`dan qayta import MVPda bor → D-117 majburiy |
| **D-11O** | AI tarjima: bitta mashq yoki tanlangan ommaviy. Importda avtomatik AI tarjima **yo'q** |
| **D-11P** | AI batch'dan oldin ko'rsatiladi: mashq soni, til, taxminiy token, taxminiy narx. `AI_MONTHLY_BUDGET_USD` limiti; limitga yetganda yangi batch bloklanadi |
| **D-11Q** | AI promptlar **faylda** qoladi (`backend/app/ai/prompts/*.txt`), Git bilan versiyalanadi. Bazaga o'tkazish MVPda yo'q |
| **D-11R** | AI tarjima — ARQ fon ishi; admin panelda `queued \| running \| completed \| failed \| cancelled` progressi |

---

## 12. Audit va moderatsiya

| ID | Qaror |
|---|---|
| **D-120** | Audit logga: admin panelga kirish, muvaffaqiyatsiz admin urinishi, user ma'lumotini ko'rish, import/eksport, ommaviy tarjima tasdiqlash, ban/unban, rol o'zgarishi, mashq CRUD, dastur publish/archive/delete, AI tarjima start/cancel, media/litsenziya o'zgarishi, barcha destruktiv amallar |
| **D-121** | O'zgarish **diff**i saqlanadi: faqat o'zgargan maydonlar `{before, after}` JSONB'da |
| **D-122** | Audit log **append-only** — `super_admin` ham UPDATE/DELETE qila olmaydi (DB darajasida) |
| **D-123** | Audit saqlash muddati — 1 yil, keyin arxiv |
| **D-124** | Audit UI: aktor/amal/obyekt/sana/target user bo'yicha filtr + CSV eksport |
| **D-125** | MVPda foydalanuvchi kontenti **shaxsiy**. Ommaviy bo'lishi mumkin bo'lgani — faqat `is_verified` ovqat mahsulotlari |
| **D-126** | Shikoyat (report) tizimi MVPda yo'q |
| **D-127** | AI'da xavfsizlik cheklovlari majburiy: ekstremal kaloriya cheklovi, xavfli trening, tibbiy tashxis, dori maslahati, ovqatlanish buzilishiga undovchi tavsiyalar |

---

## 13. Nutrition

| ID | Qaror |
|---|---|
| **D-130** | `food_items` hozir **bo'sh**. To'ldiriladi: USDA FoodData Central (asosiy) + qo'lda ~100–200 mahalliy taom (osh, somsa, mastava, sho'rva, non, manti, lag'mon, chuchvara, norin, qozon kabob va b.) |
| **D-131** | Har mahsulotda `source` + `source_reference` — ozuqa qiymati manbasi keyin tekshirilishi mumkin |
| **D-132** | Foydalanuvchi yaratgan mahsulot default **shaxsiy**; admin tasdiqlagach umumiy bazaga (`is_verified=true`) |
| **D-133** | **`food_item_servings(name, grams, is_default)`** — "1 dona somsa = 150 g", "1 piyola = 250 g" |

---

## 14. Maxfiylik va ma'lumot

| ID | Qaror |
|---|---|
| **D-140** | Hosting joyi **yuridik tekshiruvdan keyin** tanlanadi. Arxitektura location-independent: DB, obyekt saqlash, zaxiralar, loglar joyi konfiguratsiya bilan almashadi. O'zbekiston hostingi — asosiy nomzod |
| **D-141** | GDPR birlamchi maqsad emas (asosiy bozor — O'zbekiston/Markaziy Osiyo), lekin privacy-by-design saqlanadi va GDPR keyin qo'shilishi mumkin |
| **D-142** | Akkaunt o'chirish: **30 kunlik yumshoq o'chirish → doimiy anonimlashtirish**. 30 kun ichida tiklash mumkin. Keyin: Telegram identity olib tashlanadi, PII tozalanadi, trening tarixi anonim qoladi, agregat statistika saqlanadi. FK butunligi buzilmaydi |
| **D-143** | O'chirishni user (Mini App: ogohlantirish → yakuniy tasdiq) yoki admin (sabab + audit) boshlaydi. OTP shart emas; re-auth/confirmation arxitekturasi ochiq qoladi |
| **D-144** | Ma'lumot eksporti: JSON + CSV. Asosiy yetkazish — **bot orqali fayl** (Telegram WebView'da yuklab olish cheklangan). Mini App'da ham endpoint bo'lishi mumkin |
| **D-145** | Saqlash muddatlari: audit 1 yil · AI suhbatlari 90 kun · ovqat rasmlari 30 kun · refresh token yozuvlari muddat+30 kun · faol bo'lmagan akkaunt 24 oy → ogohlantirish → anonimlashtirish · trening tarixi cheksiz. Muddatlar konfiguratsiya orqali o'zgaradi |
| **D-146** | Loglarda **hech qachon**: raw `initData`, access/refresh token, cookie, sirlar, yuklangan rasm mazmuni, raw sog'liq/ovqat mazmuni. `telegram_id` maskalanadi; ichki `user_id` (UUID) ruxsat |
| **D-147** | Maxfiylik siyosati va foydalanish shartlari sahifalari MVPda bo'ladi — **texnik/mahsulot qoralamasi sifatida**, yuridik maslahat emas; keyin yurist ko'rib chiqadi |
| **D-148** | Tashqi analitika (PostHog/GA/Amplitude) **yo'q**. Ichki metrika va audit yetadi |

---

## 15. Rate limiting

| ID | Qaror |
|---|---|
| **D-150** | IP-only limiter **ishlatilmaydi** (CGNAT sababli haqiqiy foydalanuvchilar bloklanadi). Autentifikatsiyasiz → IP + `telegram_id`; autentifikatsiyalangan → `user_id`; admin → admin `user_id` |
| **D-151** | `POST /workout-sessions/{id}/sets/batch` — 50 setgacha, har biri `client_event_id` bilan, idempotent. Set uchun token bucket: burst 100, refill 20/daqiqa. **Rate limit sababli trening ma'lumoti yo'qolmasin** |
| **D-152** | Limitlar: telegram-webapp 60/min (IP) va 10/min (telegram_id) · refresh 60/min/user · exercises read 300/min · set/batch 100 burst 20/min · AI 20/kun + oylik token byudjeti · nutrition image 30/kun · admin oddiy 120/min · admin bulk 10/soat. Real metrikalar asosida sozlanadi |
| **D-153** | Redis ishlamasa: oddiy foydalanuvchi endpointlari **fail-open**, admin/destruktiv endpointlar **fail-closed** |
| **D-154** | 429 javobida `Retry-After`; klientda eksponensial backoff + jitter (offline navbat uchun majburiy) |
| **D-155** | Mashqlar katalogi **faqat autentifikatsiyalangan** foydalanuvchilar uchun (ochiq public API emas) |

---

## 16. Deploy va infratuzilma

| ID | Qaror |
|---|---|
| **D-160** | Bitta VPS + Docker Compose (Postgres, Redis, backend, frontend, bot, worker). Kubernetes kerak emas |
| **D-161** | Miqyos maqsadi: MVP 1 000 faol user → 10 000 → keyin 50 000+. Bitta server ~10k gacha; bottleneck monitoring orqali aniqlanadi |
| **D-162** | HTTPS majburiy. Cloudflare/reverse proxy ortida ishlashga tayyor; CSP va cookie xavfsizligi proxy bilan birga test qilinadi |
| **D-163** | Muhitlar: **production + staging**, har biriga alohida bot (bitta bot = bitta Mini App URL). Development — lokal long polling |
| **D-164** | CI (GitHub Actions): har PR'da backend/frontend/bot testlari, lint, type-check, build. `main`ga merge → staging avtomatik deploy. **Production deploy — qo'lda tasdiq bilan** |
| **D-165** | Zaxira: kunlik to'liq Postgres backup, imkon bo'lsa WAL/PITR; boshqa server/obyekt saqlashda. Retention: kunlik 30 kun, haftalik 3 oy. **Oyiga kamida 1 marta stagingga restore testi.** Redis — haqiqat manbai emas |
| **D-166** | Monitoring: Sentry (backend+frontend), uptime, Postgres/Redis metrikalari, CPU/RAM/disk ogohlantirishlari, AI xarajat ogohlantirishi. Markazlashtirilgan log — keyin |
| **D-167** | Sirlar: serverdagi `.env`, `chmod 600`, Git'ga hech qachon tushmaydi. Secret managerga o'tish keyin. JWT siri almashtirilishi sessiyalarni invalidatsiya qiladi — silent re-auth tufayli qabul qilinarli |
| **D-168** | Bot: production → **webhook**, development → long polling |
| **D-169** | Migratsiya — **alohida deploy qadami**, konteyner startida avtomatik emas. Pipeline: `backup → migration → backend → frontend → bot → health check`. Migratsiya backward-compatible |

---

## 17. API konvensiyalari

| ID | Qaror |
|---|---|
| **D-170** | **Atomik reliz.** Backend + frontend + bot birga yangilanadi; `/api/v2` yaratilmaydi; parol endpointlari olib tashlanadi |
| **D-171** | Javob shakli: muvaffaqiyat — yalang'och obyekt; xato — `{success:false, error:{code, message}}`. Global `{success:true,data:{}}` konverti yo'q |
| **D-172** | Nomlash: hamma joyda **`snake_case`** (`body_part`, `page_size`, `tracking_type`) |
| **D-173** | Sahifalash: trening tarixi va audit log → **kursor**; admin/katalog ro'yxatlari → offset; kichik statik lookup'lar → sahifalashsiz |
| **D-174** | `GET /workouts` va o'sib boradigan barcha ro'yxatlar sahifalanadi |
| **D-175** | FastAPI OpenAPI — hujjatning haqiqat manbai. `docs/API.md` qo'lda yozilmaydi, generatsiya qilinadi |

---

## 18. O'zgarmas invariantlar

Bu qoidalar har bosqichda, har PR'da amal qiladi. Buzilishi — bloklovchi xato.

1. **Tarix o'zgarmas.** Dastur yoki reja keyin o'zgarsa, tugallangan sessiya tarixi o'zgarmaydi.
2. **Published dastur o'zgarmas.** Tahrir → yangi versiya.
3. **Klon.** Dastur boshlanganda butun struktura snapshot qilinadi.
4. **Idempotentlik.** Bir xil `client_event_id` dublikat yozuv yaratmaydi.
5. **Soft delete.** Tarixga aloqador obyektlar hard delete qilinmaydi; tarixiy FK'lar buzilmaydi.
6. **Auditlik.** Admin amallari va foydalanuvchi ma'lumotini ko'rish audit logga tushadi; audit log append-only.
7. **AI hech qachon avtomatik approve qilmaydi.**
8. **Admin override importdan ustun.**
9. **Numeric.** Barcha o'lchov/vazn/ozuqa qiymatlari `NUMERIC`/`Decimal`.
10. **Telegram identity server tomonda tekshiriladi.** Klientdan kelgan `telegram_id`ga hech qachon ishonilmaydi.
11. **Admin va user API huquqlari qat'iy ajratilgan.**
12. **Multi-tenant seam saqlanadi**, lekin `organization_id` MVPda qo'shilmaydi.
13. **Kunlik statistika `Asia/Tashkent` bo'yicha.**
14. **Xavfsizlik/maxfiylik — kechiktiriladigan feature emas.** Har bosqichda authentication, authorization, validation, rate limiting, audit, privacy, input sanitization, error handling va secret management o'z qamrovida tekshiriladi. 10-bosqich — yakuniy audit, birinchi ko'rib chiqish emas.
15. **DB darajasidagi cheklovlar** biznes qoidalarini himoya qiladi, faqat Python validatsiyasi emas.

---

## 19. Ochiq masalalar (qaror qabul qilinmagan)

| # | Masala | Kim hal qiladi | Nimani bloklaydi |
|---|---|---|---|
| **O-1** | **Media litsenziyasi.** GIF'lar `JahelCuadrado/ExerciseGymGifsDB` repozitoriyasidan; uning README'si mualliflik huquqiga egalik qilmasligini aytadi | Mahsulot egasi + yurist | Commercial production release (D-85). Development/beta bloklanmaydi |
| **O-2** | **Ma'lumot lokalizatsiyasi.** O'zbekiston shaxsiy ma'lumotlar qonuni talablari | Yurist | Production hosting tanlash (D-140) |
| **O-3** | **Domen va hosting provayderi** | Mahsulot egasi | 11-bosqich (deploy) |
| **O-4** | **Test qurilmalari** — qaysi klientlar fizik mavjud (Android/iOS/Desktop/Web) | Mahsulot egasi | 0-bosqich test matritsasi |
| **O-5** | **Dastur mazmunini kim yozadi** — 6 ta boshlang'ich dasturning mashq tanlovi va target'lari (D-79) | Mahsulot egasi yoki murabbiy | 4-bosqich yakuni |
| **O-6** | **O'zbekcha fitnes atamalari lug'ati** (D-97) — "set", "rep", "failure", "warm-up" kabi 50–100 atamaning tasdiqlangan tarjimasi | Mahsulot egasi | 8-bosqich |
| **O-7** | **Mahalliy ovqat ma'lumotlari manbasi** (D-130) — ochiq manbadan yig'ilsinmi yoki mahsulot egasi beradimi | Mahsulot egasi | 9-bosqich |
| **O-8** | **OpenAI API kaliti** — hali berilmagan | Mahsulot egasi | AI xususiyatlari va AI tarjima (8-bosqich). Qolgan hamma narsa bloklanmaydi |

---

*Oxirgi yangilanish: 5-raund yakunida. Qaror o'zgarganda shu jadvallar o'zgarish bilan bir
commitda yangilanadi.*
