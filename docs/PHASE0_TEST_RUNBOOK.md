# 0-bosqich — real qurilmada test qilish yo'riqnomasi

**Kimga:** mahsulot egasiga · **Qancha vaqt:** tayyorgarlik ~15 daqiqa (bir marta), keyin har
qurilmada ~5 daqiqa · **Qurilmalar:** Android Telegram, iOS Telegram, Telegram Desktop

Maqsad — `docs/DECISIONS.md` D-13 (cookie sessiyasi), D-15 (silent re-auth), D-16/D-17
(`initData`) va D-19 (CSRF headerlari) qarorlarini **haqiqiy Telegram WebView'da** o'lchash.
Chromium simulyatsiyasi bularni **isbotlamaydi** — u faqat brauzer haqidagi dalil.

---

## 0. Xavfsizlik qoidalari — avval o'qing

| Qoida | Sabab |
|---|---|
| **Bot tokenini menga, chatga, PR'ga yoki logga yozmang.** U faqat serveringizdagi `.env` faylida turadi | Token bilan istalgan odam bot nomidan ish qila oladi va `initData` imzosini soxtalashtira oladi |
| **Test uchun alohida bot yarating** (`@BotFather` → `/newbot`), asosiy botni ishlatmang | Tunnel manzili ommaviy; test boti bilan xavf nolga yaqin |
| **Tunnel faqat test paytida ochiq tursin**, tugagach yoping | Tunnel URL'i internetdan ochiq; diagnostika endpointlari autentifikatsiyasiz |
| **`DEBUG=true` faqat lokal/staging'da**. Production'da hech qachon | Diagnostika marshrutlari faqat DEBUG'da mavjud (D: 5-talab) |
| `.env` faylini commit qilmang | `.gitignore`da bor, lekin tekshiring: `git status` da `.env` ko'rinmasligi kerak |
| `.env` huquqlari: `chmod 600 .env` | Bir mashinada bir nechta foydalanuvchi bo'lsa |

Diagnostika endpointlari ataylab **hech kimni tizimga kiritmaydi, token bermaydi, akkaunt
yaratmaydi va bazaga tegmaydi**; `telegram_id` va cookie qiymati maskalanadi. Shunga qaramay
ular autentifikatsiyasiz — shuning uchun tunnelni uzoq ochiq qoldirmang.

---

## 1. Tayyorgarlik (bir marta)

### 1.1 Test boti

`@BotFather` → `/newbot` → nom bering → **token beradi**. Tokenni **faqat nusxalab oling**,
hech qayerga yozmang — keyingi qadamda to'g'ridan-to'g'ri `.env` ga qo'yasiz.

### 1.2 `.env` faylini tayyorlash

Loyiha ildizida (`TEST/.env`):

```bash
cp .env.example .env
chmod 600 .env
```

Keyin `.env` ni tahrirlab, **aynan shu to'rt qatorni** to'ldiring:

```ini
# 1) BotFather bergan token — faqat shu yerda, boshqa hech qayerda
TELEGRAM_BOT_TOKEN=<BotFather bergan token>

# 2) Diagnostika marshrutlari faqat shunda mavjud bo'ladi
DEBUG=true

# 3) JWT sirlari — diagnostika uchun ishlatilmaydi, lekin backend ishga tushishi uchun kerak.
#    Tasodifiy qiymat yarating:  openssl rand -hex 32
JWT_SECRET=<tasodifiy>
JWT_REFRESH_SECRET=<boshqa tasodifiy>

# 4) FRONTEND_URL ni hozircha bo'sh qoldiring — 1.4 da to'ldiramiz
FRONTEND_URL=
```

> `.env.example` da `DEBUG` qatori yo'q — uni qo'lda qo'shing. Qiymat berilmasa ham default
> `true`, lekin aniq yozib qo'ygan ma'qul.

### 1.3 Loyihani ishga tushirish

**Docker bilan (Linux / macOS):**
```bash
make up
make migrate
make seed
```

**Docker bilan (Windows / PowerShell)** — `make` odatda o'rnatilmagan va PowerShell 5.1 da `&&`
operatori yo'q, shuning uchun har buyruqni **alohida qatorda** yozing:

```powershell
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/import_exercises.py
docker compose exec backend python scripts/seed_database.py
```

To'liq Windows buyruqlari jadvali — §7.

> **`--build` ni tushirib qoldirmang.** `docker-compose.yml` da `backend` xizmatining kodi
> volume orqali ulangan, lekin **`frontend` va `telegram-bot` xizmatlarida bunday emas** —
> ularning kodi image ichiga qotib qoladi. Ya'ni `git pull` qilganingizdan keyin
> `docker compose restart` yangi kodni **olmaydi**: diagnostika sahifasi ham, `/diag`
> buyrug'i ham paydo bo'lmaydi. Kod o'zgargach har doim `docker compose up -d --build`.

**Docker'siz (README dagi native yo'l):** backend `:8000`, frontend `:3000` da ishlashi kerak.
Frontend `/api/v1/*` ni backendga o'zi uzatadi — **bitta ommaviy manzil yetarli**, backendni
alohida ochish shart emas va CORS sozlash kerak emas.

Tekshiruv (Linux / macOS):
```bash
curl -s http://localhost:3000/_diag/webview.html | head -3      # sahifa bormi
curl -s http://localhost:8000/api/v1/_diag/env                   # DEBUG rejimi ishlayaptimi
```

Tekshiruv (Windows / PowerShell) — PowerShell'da `curl` aslida `Invoke-WebRequest` uchun
taxallus va `-s` bayrog'ini tushunmaydi, shuning uchun boshqa buyruq ishlatiladi:
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/_diag/env
(Invoke-WebRequest http://localhost:3000/_diag/webview.html).StatusCode
```

Birinchisi JSON qaytarishi kerak. `404` qaytsa — `DEBUG` `true` emas.

### 1.4 Tunnel

Telegram faqat haqiqiy `https://` manzilni qabul qiladi — `http://` ham, `localhost` ham
ishlamaydi.

```bash
ngrok http 3000
# chiqadi: https://xxxx-xx-xx.ngrok-free.app
```

`.env` da **faqat shu bitta qatorni** yangilang:

```ini
FRONTEND_URL=https://xxxx-xx-xx.ngrok-free.app
```

> Diagnostika sahifasiga alohida yo'naltirish **kerak emas** — botning `/diag` buyrug'i uni shu
> manzildan o'zi hosil qiladi. Ya'ni test tugagach `FRONTEND_URL` ni orqaga qaytarish ham
> shart emas.

Botni yangi manzil bilan qayta yarating:

```bash
docker compose up -d --build telegram-bot
```
*(Bu buyruq Windows'da ham aynan shunday.)*

> `restart` emas, `up -d` — `docker compose restart` konteynerni o'sha eski muhit
> o'zgaruvchilari bilan qayta ishga tushiradi va `.env` dagi yangi `FRONTEND_URL` ni
> **o'qimaydi**. `--build` esa botning yangi kodini oladi.

> Ngrok'ning bepul tarifida URL har qayta ishga tushirishda o'zgaradi. O'zgarsa — `FRONTEND_URL`
> ni yangilang va botni qayta ishga tushiring.

**Ngrok ogohlantirish sahifasi.** Bepul tarifda ngrok birinchi tashrifda "You are about to visit…"
oraliq sahifasini ko'rsatadi. Telegram ichida u ham ochiladi — **"Visit Site"** tugmasini bosing,
keyin diagnostika sahifasi chiqadi. Agar bu Mini App'da muammo tug'dirsa (ayniqsa iOS'da),
oraliq sahifasi bo'lmagan muqobilni ishlating:

```bash
cloudflared tunnel --url http://localhost:3000
```

---

## 2. Har qurilmada test (≈5 daqiqa)

Uchala qurilmada **alohida-alohida** bajaring: Android → iOS → Desktop.

1. Telegram'da test botini oching → **`/diag`** yuboring → **"🔬 Diagnostikani ochish"**.
   *(`/start` dagi "Open App" tugmasi odatdagi ilovani ochadi — diagnostika uchun `/diag` kerak.)*
2. **1-tugma — "Asosiy tekshiruv"**. Jadval to'ladi, tepada xulosa qatori chiqadi.
3. Mini App'ni **butunlay yoping**: orqaga tugmasi emas — Mini App'ni yoping va **chatdan ham
   chiqing**. Telegram'ni butunlay yopib qayta ochsangiz yanada ishonchli.
4. Botni qayta oching → **`/diag`** → **"🔬 Diagnostikani ochish"** → **2-tugma — "Qayta ochgandan keyin"**.
   *Bu eng muhim qadam: D-14 dagi 7 kunlik sessiya aynan shunga bog'liq.*
5. **3-tugma — "Silent re-auth testi"**. Bu cookie'ni **ataylab o'chiradi** va `initData` bilan
   qayta ishlashini tekshiradi. Shuning uchun uni **faqat 2-tugmadan keyin** bosing.
6. **4-tugma — "Natijani nusxalash"** → JSON'ni menga yuboring.

JSON'da shaxsiy ma'lumot yo'q: `telegram_id` maskalangan (`*******853`), cookie qiymati
maskalangan, `initData` esa faqat qisqa fingerprint sifatida (6 bayt hash) yoziladi — payloadning
o'zi hech qachon hisobotga tushmaydi.

---

## 3. Qayd etiladigan 10 band — qaysi tugma qaysi bandni beradi

| # | Band | Tugma | Hisobotdagi joyi |
|---|---|---|---|
| 1 | `Set-Cookie` qabul qilindimi | 1 | `steps.set_cookie.body.set_cookie_sent` |
| 2 | `Secure` / `SameSite=None` / `Partitioned` holati | 1 | `steps.attributes_survived` + `cookie_attributes` |
| 3 | Yopib qayta ochganda cookie saqlanadimi | **2** | `steps.reopen.cookie_returned` |
| 4 | `initData` mavjudmi | 1 | `telegram.has_init_data` |
| 5 | Qayta ochilganda payload o'zgardimi | **2** | `steps.reopen.init_data_changed` (fingerprint solishtiruvi) |
| 6 | `auth_date` va 300s freshness | 1 va 2 | `steps.init_data.body.auth_date` / `.within_300s_window` |
| 7 | POST so'rovda `Origin` bormi | 1 | `steps.init_data.body.observed.origin` |
| 8 | `Referer` bormi | 1 | `steps.init_data.body.observed.referer` |
| 9 | Cookie ishlamagan holatda silent re-auth | **3** | `steps.silent_reauth.init_data_ok` |
| 10 | Native WebView bo'yicha amaliy xulosa | avtomatik | `verdict` (ekranda ham ko'rinadi) |

Qo'shimcha ravishda D-17 ham o'lchanadi: `steps.init_data_replay` — **aynan bir xil `initData`
ikkinchi marta yuborilganda ham qabul qilinishi**. Bu `false` chiqsa, bir martalik nonce qoidasi
kirib qolgan va legitim reload buziladi.

### 5-bandga izoh

Fingerprint solishtiruvi `localStorage`ga tayanadi. Agar WebView `localStorage`ni ham tozalab
yuborsa, natija `null` bo'ladi ("solishtirib bo'lmadi") — bu **ham qimmatli natija**: iOS
WKWebView'da aynan shu kutiladi. Bunday holatda 1-tugma bosilgandagi `auth_date` qiymatini
qo'lda yozib qo'ying va 2-tugmadagi `auth_date` bilan solishtiring.

---

## 4. Test tugagach — tozalash

```bash
# 1. Tunnelni yoping (ngrok/cloudflared oynasida Ctrl+C)
# 2. Boshqa hech narsa shart emas — FRONTEND_URL odatdagi manzil bo'lib qolgan.
```

Test botini `@BotFather` → `/deletebot` orqali o'chirib yuborsangiz ham bo'ladi.
Diagnostika kodi (`/diag` buyrug'i, `_diag` marshrutlari, sahifa) 0-bosqich yopilgach men
tomonidan olib tashlanadi — `docs/TELEGRAM_WEBVIEW_MATRIX.md` §7.

---

## 5. Natijani yuborish

Har uchala qurilmadan nusxalangan JSON'ni yuboring. Bitta gap qo'shsangiz kifoya, masalan:

```
Android: <JSON>
iOS: <JSON>
Desktop: <JSON>
```

Men ularni `docs/TELEGRAM_WEBVIEW_MATRIX.md` §5.3 matritsasiga kiritaman va **shundan keyin**
D-13 / D-15 / D-19 bo'yicha yakuniy xulosa yozaman.

---

## 6. Nimadir ishlamasa

| Alomat | Sabab va yechim |
|---|---|
| `/api/v1/_diag/env` → **404** | `DEBUG` `true` emas. `.env` ni tekshiring va backendni qayta ishga tushiring |
| `/diag` "FRONTEND_URL https:// bo'lishi kerak" deydi | `.env` dagi `FRONTEND_URL` bo'sh yoki `http://`. Tunnel manzilini qo'ying va botni qayta ishga tushiring |
| `/diag` buyrug'i umuman javob bermaydi | Bot image'i eski. `git pull` qiling va **`docker compose up -d --build telegram-bot`** (`restart` yetarli emas — bot kodi volume orqali ulanmagan) |
| Diagnostika sahifasi 404 beradi | Frontend image'i eski: `docker compose up -d --build frontend` |
| `.env` ni o'zgartirdim, lekin ta'sir qilmadi | `restart` `.env` ni qayta o'qimaydi: `docker compose up -d <xizmat>` |
| Ngrok "You are about to visit…" sahifasi chiqdi | Bu normal — **"Visit Site"** ni bosing. Halaqit bersa `cloudflared` ga o'ting (§1.4) |
| Sahifa ochiladi, lekin "Telegram SDK: YO'Q" | Sahifa brauzerda ochilgan. Faqat bot tugmasi orqali oching |
| "initData mavjud: YO'Q" | Xuddi shu sabab — yoki `FRONTEND_URL` noto'g'ri sahifaga yo'naltirilgan |
| Ngrok "ERR_NGROK_..." | Tunnel uzilgan; qayta oching va yangi URL bilan `FRONTEND_URL` ni yangilang |
| Barcha so'rovlar xato | Frontend `:3000` da ishlayaptimi va backendga proksi qilyaptimi tekshiring |

Xatoni hal qila olmasangiz — ekran rasmini yuboring, tokensiz. **Xato matnida token
ko'rinmasligiga ishonch hosil qiling.**

---

## 7. Windows (PowerShell) buyruqlari

PowerShell 5.1 (Windows'dagi standart) Unix qobig'idan uch joyda farq qiladi va uchalasi ham bu
yo'riqnomada uchraydi.

| Farq | Unix'da | PowerShell'da |
|---|---|---|
| Buyruqlarni ulash | `make up && make migrate` | `&&` **yo'q** — har buyruq alohida qatorda |
| `make` | o'rnatilgan | odatda **yo'q** — `docker compose` ni to'g'ridan-to'g'ri chaqiring |
| `curl` | haqiqiy curl | `Invoke-WebRequest` uchun taxallus; `-s` kabi bayroqlarni tushunmaydi |

> PowerShell 7+ da `&&` ishlaydi. Versiyani tekshirish: `$PSVersionTable.PSVersion`

### Makefile maqsadlarining PowerShell muqobili

| `make` | PowerShell |
|---|---|
| `make up` | `docker compose up -d --build` |
| `make down` | `docker compose down` |
| `make logs` | `docker compose logs -f` |
| `make migrate` | `docker compose exec backend alembic upgrade head` |
| `make seed` | `docker compose exec backend python scripts/import_exercises.py`<br>`docker compose exec backend python scripts/seed_database.py` |
| `make test-bot` | `docker compose exec telegram-bot pytest` |
| `make backend-shell` | `docker compose exec backend bash` |

`make up` fonda ishlamaydi (terminalni band qiladi) — Windows'da `-d` qo'shilgani shuning uchun:
keyingi buyruqlarni o'sha oynada yozishingiz mumkin. Loglarni ko'rish uchun
`docker compose logs -f telegram-bot`.

### Qaysi xizmat qachon qayta qurilishi kerak

| Xizmat | Kod volume orqali ulanganmi | Kod o'zgargach |
|---|---|---|
| `backend` | ✅ ha (`./backend:/app`) | `docker compose restart backend` yetadi |
| `frontend` | ❌ yo'q | **`docker compose up -d --build frontend`** |
| `telegram-bot` | ❌ yo'q | **`docker compose up -d --build telegram-bot`** |

`.env` o'zgarganda esa uchalasi uchun ham `up -d` kerak — `restart` muhit o'zgaruvchilarini
qayta o'qimaydi. Shubha bo'lsa, hamma narsani qamrab oladigan bitta buyruq:
`docker compose up -d --build`.

### Boshqa muqobillar

```powershell
# .env yaratish
Copy-Item .env.example .env

# Tasodifiy JWT siri (openssl rand -hex 32 o'rniga)
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })

# Faqat bir xizmatni qayta ishga tushirish
docker compose restart telegram-bot

# Backend loglarini ko'rish (DEBUG ishlayaptimi tekshirish uchun)
docker compose logs --tail 50 backend
```

`.env` huquqlari: Unix'dagi `chmod 600` o'rniga Windows'da fayl sizning foydalanuvchi
profilingiz ichida tursa yetarli. Umumiy mashinada bo'lsa:
```powershell
icacls .env /inheritance:r /grant:r "$env:USERNAME:(R,W)"
```
