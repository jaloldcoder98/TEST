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

**Docker bilan:**
```bash
make up
make migrate
make seed
```

**Docker'siz (README dagi native yo'l):** backend `:8000`, frontend `:3000` da ishlashi kerak.
Frontend `/api/v1/*` ni backendga o'zi uzatadi — **bitta ommaviy manzil yetarli**, backendni
alohida ochish shart emas va CORS sozlash kerak emas.

Tekshiruv:
```bash
curl -s http://localhost:3000/_diag/webview.html | head -3      # sahifa bormi
curl -s http://localhost:8000/api/v1/_diag/env                   # DEBUG rejimi ishlayaptimi
```
Ikkinchisi JSON qaytarishi kerak. `404` qaytsa — `DEBUG` `true` emas.

### 1.4 Tunnel va bot tugmasi

Telegram faqat haqiqiy `https://` manzilni qabul qiladi — `http://` ham, `localhost` ham
ishlamaydi.

```bash
ngrok http 3000
# chiqadi: https://xxxx-xx-xx.ngrok-free.app
```

`.env` da `FRONTEND_URL` ni **to'g'ridan-to'g'ri diagnostika sahifasiga** yo'naltiring:

```ini
FRONTEND_URL=https://xxxx-xx-xx.ngrok-free.app/_diag/webview.html
```

Botni qayta ishga tushiring, u yangi tugma manzilini o'qib olsin:

```bash
docker compose restart telegram-bot        # yoki botni qayta ishga tushiring
```

> Bu vaqtinchalik: `FRONTEND_URL` bot tugmasi qaysi sahifani ochishini belgilaydi. Test tugagach
> uni odatdagi manzilga qaytarasiz (§4).
>
> Ngrok'ning bepul tarifida URL har qayta ishga tushirishda o'zgaradi — o'zgarsa, `FRONTEND_URL`
> ni yangilab, botni qayta ishga tushiring.

---

## 2. Har qurilmada test (≈5 daqiqa)

Uchala qurilmada **alohida-alohida** bajaring: Android → iOS → Desktop.

1. Telegram'da test botini oching → `/start` → **"Ilovani ochish / Open App"**.
2. **1-tugma — "Asosiy tekshiruv"**. Jadval to'ladi, tepada xulosa qatori chiqadi.
3. Mini App'ni **butunlay yoping**: orqaga tugmasi emas — Mini App'ni yoping va **chatdan ham
   chiqing**. Telegram'ni butunlay yopib qayta ochsangiz yanada ishonchli.
4. Botni qayta oching → **Open App** → **2-tugma — "Qayta ochgandan keyin"**.
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
# 1. Tunnelni yoping (ngrok oynasida Ctrl+C)

# 2. .env da FRONTEND_URL ni odatdagi manzilga qaytaring (yoki bo'sh qoldiring)
FRONTEND_URL=

# 3. Botni qayta ishga tushiring
docker compose restart telegram-bot
```

Test botini `@BotFather` → `/deletebot` orqali o'chirib yuborsangiz ham bo'ladi.

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
| Botda "Open App" tugmasi yo'q | `FRONTEND_URL` `https://` bilan boshlanmayapti yoki bot qayta ishga tushirilmagan |
| Sahifa ochiladi, lekin "Telegram SDK: YO'Q" | Sahifa brauzerda ochilgan. Faqat bot tugmasi orqali oching |
| "initData mavjud: YO'Q" | Xuddi shu sabab — yoki `FRONTEND_URL` noto'g'ri sahifaga yo'naltirilgan |
| Ngrok "ERR_NGROK_..." | Tunnel uzilgan; qayta oching va yangi URL bilan `FRONTEND_URL` ni yangilang |
| Barcha so'rovlar xato | Frontend `:3000` da ishlayaptimi va backendga proksi qilyaptimi tekshiring |

Xatoni hal qila olmasangiz — ekran rasmini yuboring, tokensiz. **Xato matnida token
ko'rinmasligiga ishonch hosil qiling.**
