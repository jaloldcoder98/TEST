# 0-bosqich — Telegram WebView test matritsasi

**Maqsad:** `docs/DECISIONS.md` D-13 (cookie sessiyasi), D-15 (silent re-auth), D-16/D-17
(`initData` freshness va replay) va D-19 (CSRF qatlamlari) qarorlarini **taxmin qilmasdan,
o'lchab** tasdiqlash — auth kodi yozilishidan oldin.

**Holat:** 0-bosqich **OCHIQ**. Kod va simulyatsiya qismi mahsulot egasi tomonidan qabul
qilindi; uchta fizik qurilma testi kutilmoqda. Yo'riqnoma: `docs/PHASE0_TEST_RUNBOOK.md`.

> ⚠️ **`Partitioned` cookie Chromium simulyatsiyasida ishlagani Telegram Android/iOS/Desktop
> WebView'da ham aynan shunday ishlashini isbotlamaydi.** Real test natijalarisiz D-13/D-15
> bo'yicha yakuniy xulosa chiqarilmaydi. Bu §6 dagi barcha mulohazalarga taalluqli.

---

## 1. Nima bajarildi va nima bajarilmadi

| Ish | Kim | Holat |
|---|---|---|
| Diagnostika endpointlari (`/api/v1/_diag/*`, faqat DEBUG) | Claude | ✅ yozildi va testdan o'tdi |
| Diagnostika sahifasi (`/_diag/webview.html`) | Claude | ✅ yozildi |
| Chromium cross-site iframe simulyatsiyasi | Claude | ✅ bajarildi, natijalar §4 da |
| **Android Telegram — real test** | **Mahsulot egasi** | ⏳ kutilmoqda |
| **iOS Telegram — real test** | **Mahsulot egasi** | ⏳ kutilmoqda |
| **Telegram Desktop — real test** | **Mahsulot egasi** | ⏳ kutilmoqda |
| Telegram Web (Chrome/Safari/Firefox) — real test | — | ❌ fizik muhit yo'q (O-4) |

### Nega fizik testlarni men bajara olmayman

Bu sessiya izolyatsiyalangan konteynerda ishlaydi. Uchta narsa yetishmaydi va ularning
hech biri kod bilan hal qilinmaydi:

1. **Telegram klienti yo'q** — Mini App'ni ochish uchun haqiqiy Telegram ilovasi va hisob kerak.
2. **Ommaviy HTTPS manzil yo'q** — Telegram Mini App'ni faqat haqiqiy `https://` domendan
   yuklaydi. Konteyner tashqaridan kirish uchun ochiq emas va tunnel vositasi (ngrok,
   cloudflared) o'rnatilmagan hamda tarmoq siyosati buni bloklaydi.
3. **`TELEGRAM_BOT_TOKEN` yo'q** — `.env` mavjud emas, token berilmagan. Tokensiz `initData`
   imzosini tekshirib bo'lmaydi.

Shuning uchun bu bosqich ikkiga bo'lindi: **men vositani quraman va brauzer darajasidagi
dalilni yig'aman**, **siz uchta qurilmada 5 daqiqalik testni bajarasiz** (§5 dagi qo'llanma).

---

## 2. Fizik muhitlar (O-4 javobiga ko'ra)

| Muhit | Fizik mavjud | Test usuli |
|---|---|---|
| Android Telegram | ✅ **BOR** | Real HTTPS staging testi |
| iOS Telegram | ✅ **BOR** | Real HTTPS staging testi |
| Telegram Desktop | ✅ **BOR** | Real HTTPS staging testi |
| Telegram Web + Chrome | ❌ **YO'Q** | Chromium simulyatsiyasi (§4) — **ekvivalent emas** |
| Telegram Web + Safari | ❌ **YO'Q** | Simulyatsiya ham yo'q — WebKit dvigateli mavjud emas |
| Telegram Web + Firefox | ❌ **YO'Q** | Simulyatsiya ham yo'q — Gecko dvigateli mavjud emas |

Playwright'ning Firefox va WebKit brauzerlarini yuklab olishga urinish tarmoq siyosati
tomonidan bloklandi (`Failed to download Firefox 142.0.1`), shuning uchun bu ikki dvigatel
uchun **hech qanday empirik ma'lumot yo'q** — na real, na simulyatsiya.

---

## 3. Har muhitda o'lchanadigan narsalar

| # | Tekshiruv | Nima uchun |
|---|---|---|
| 1 | `__Host-` prefiksli cookie o'rnatiladimi | D-13 |
| 2 | `Secure` atributi qabul qilinadimi | D-13 |
| 3 | `SameSite=None` qabul qilinadimi | Telegram Web iframe uchun shart |
| 4 | `Partitioned` (CHIPS) qabul qilinadimi | D-13, Chrome 3P bloklashi |
| 5 | Cookie **qayta ochgandan keyin** saqlanadimi | D-14 (7 kunlik sessiya) |
| 6 | `httpOnly` haqiqatan JS'dan yashiradimi | D-12 |
| 7 | `initData` mavjudmi | D-10 |
| 8 | `initData` yoshi (freshness) | D-16 (300s) |
| 9 | **Aynan bir xil `initData` qayta yuborilsa qabul qilinadimi** | D-17 — legitim reload buzilmasligi |
| 10 | `Origin` header serverga yetadimi | D-19 (qo'shimcha qatlam) |
| 11 | `Referer` header serverga yetadimi | D-19 |
| 12 | Cookie yo'q holatda `initData` bilan silent re-auth ishlaydimi | D-15, invariant 16 |

---

## 4. Chromium simulyatsiyasi — bajarildi

`tools/webview-sim/run.mjs`. Ikkita **haqiqatan turli sayt** (`https://127.0.0.1:8443` —
"Mini App", `https://localhost:8444` — "Telegram Web") HTTPS orqali ishga tushiriladi va
birinchisi ikkinchisining `<iframe>`iga joylashtiriladi. Uchinchi tomon cookie'lari CDP'ning
`Network.setCookieControls` buyrug'i bilan bloklanadi — bu DevTools'ning "block third-party
cookies" tugmasi bosgan o'sha kalit.

**Chromium 141.0.7390.37 · 2026-09-04**

| Stsenariy | Kontekst | 3P cookie | `Partitioned` **yo'q** | `Partitioned` **bor** |
|---|---|---|---|---|
| 1. Top-level (native WebView'ga teng) | top-level | ruxsat | ✅ qaytdi | ✅ qaytdi |
| 2. Cross-site iframe | iframe | ruxsat | ✅ qaytdi | ✅ qaytdi |
| 3. **Cross-site iframe** | iframe | **bloklangan** | ❌ **qaytmadi** | ✅ **qaytdi** |

**Headerlar (uchala stsenariyda ham bir xil):**

| So'rov turi | `Origin` | `Referer` | `Sec-Fetch-Site` |
|---|---|---|---|
| GET (same-origin) | ❌ yo'q | ✅ bor | `same-origin` |
| POST (same-origin) | ✅ bor | ✅ bor | `same-origin` |

### Bu nimani ko'rsatadi

- **`Partitioned` (D-3) hal qiluvchi ahamiyatga ega.** Uchinchi tomon cookie'lari bloklangan
  brauzerda `Partitioned`siz cookie yo'qoladi, `Partitioned` bilan omon qoladi. Bu D-13 dagi
  atributlar to'plamini to'g'ridan-to'g'ri tasdiqlaydi.
- **`__Host-` + `SameSite=None` + `Partitioned` birgalikda ishlaydi** — atributlar bir-birini
  inkor qilmaydi.
- **D-19 uchun:** `Origin` **GET so'rovda yo'q**, lekin **POST so'rovda bor**. Refresh endpointi
  POST bo'lgani uchun `Origin` unga yetib keladi — ammo bu Chromium'da; Telegram klientlarida
  qanday ekani hali o'lchanmagan. D-19 aynan shuning uchun `Origin`ni **ikkilamchi** qatlam deb
  belgilaydi va asosiy himoyani CSRF tokenida qoldiradi. Simulyatsiya bu qarorni qo'llab-quvvatlaydi.

### ⚠️ Simulyatsiyaning chegaralari — buni real test deb hisoblamang

Bu **brauzer xatti-harakati haqidagi dalil**, Telegram Web haqidagi dalil emas. Aniq farqlar:

1. **Telegram'ning o'z qobig'i modellashtirilmagan.** Haqiqiy Telegram Web iframe'ga `sandbox`,
   `allow`, `referrerpolicy` kabi atributlar qo'yishi va Content-Security-Policy qo'llashi
   mumkin — bularning hech biri bu yerda takrorlanmagan.
2. **Loopback manzillar ishlatilgan.** Sandbox DNS'i o'ylab topilgan domenlarni (`app.test`)
   hal qilmagani uchun `127.0.0.1` va `localhost` juftligi olingan. Ular Chromium uchun
   haqiqatan cross-site, lekin brauzerlar loopback manzillarga ba'zi qoidalarni yumshoqroq
   qo'llashi mumkin.
3. **CDP orqali bloklash — haqiqiy foydalanuvchi sozlamasining o'rnini bosuvchi.** Bu DevTools
   ishlatadigan mexanizm, lekin Safari ITP yoki Firefox Total Cookie Protection'ning aniq
   xatti-harakati emas.
4. **Faqat Chromium.** Safari (WebKit) va Firefox (Gecko) uchun bu natijalar **hech narsa
   demaydi**. Safari uchinchi tomon cookie'larini butunlay bloklaydi va `Partitioned`ni
   qo'llab-quvvatlamaydi — ya'ni u yerda cookie umuman ishlamasligi kutiladi va **yagona
   yechim D-15 dagi silent re-auth**.
5. **`initData`, Telegram SDK va qayta ochish sikli umuman modellashtirilmagan** — ular faqat
   real klientda tekshiriladi.

**Qayta ishga tushirish:**
```bash
cd tools/webview-sim && npm install && node run.mjs          # o'qish uchun
cd tools/webview-sim && node run.mjs --json                   # mashina uchun
```

---

## 5. Fizik qurilma testi

To'liq yo'riqnoma alohida hujjatda: **`docs/PHASE0_TEST_RUNBOOK.md`** — test boti, `.env`,
tunnel, har qurilmadagi qadamlar, tozalash va nosozliklarni bartaraf etish.

Diagnostika sahifasi to'rt qadamdan iborat va mahsulot egasi qayd etadigan 10 bandning
hammasini qamrab oladi:

| # | Band | Tugma |
|---|---|---|
| 1 | `Set-Cookie` qabul qilindimi | 1 |
| 2 | `Secure` / `SameSite=None` / `Partitioned` holati | 1 |
| 3 | Yopib qayta ochganda cookie saqlanadimi | **2** |
| 4 | `initData` mavjudmi | 1 |
| 5 | Qayta ochilganda payload o'zgardimi (fingerprint solishtiruvi) | **2** |
| 6 | `auth_date` va 300s freshness | 1, 2 |
| 7 | POST so'rovda `Origin` bormi | 1 |
| 8 | `Referer` bormi | 1 |
| 9 | Cookie yo'q holatda silent re-auth | **3** |
| 10 | Native WebView bo'yicha amaliy xulosa | avtomatik (`verdict`) |

Qo'shimcha: `steps.init_data_replay` — aynan bir xil `initData` ikkinchi marta ham qabul
qilinishi (D-17). `false` chiqsa, bir martalik nonce qoidasi kirib qolgan degani.

Hisobotda shaxsiy ma'lumot yo'q: `telegram_id` va cookie qiymati maskalangan, `initData` esa
faqat 6 baytlik fingerprint sifatida yoziladi — payloadning o'zi hech qachon hisobotga tushmaydi.

### 5.3 To'ldiriladigan matritsa

| Tekshiruv | Android | iOS | Desktop | Web/Chrome | Web/Safari | Web/Firefox |
|---|---|---|---|---|---|---|
| `__Host-` cookie o'rnatildi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| `Secure` qabul qilindi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| `SameSite=None` qabul qilindi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| `Partitioned` qabul qilindi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| Darhol qaytdi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| **Qayta ochgandan keyin qaytdi** | ⏳ | ⏳ | ⏳ | sim: yo'q | — | — |
| `httpOnly` JS'dan yashirdi | ⏳ | ⏳ | ⏳ | sim: yo'q | — | — |
| `initData` mavjud | ⏳ | ⏳ | ⏳ | — | — | — |
| `initData` yoshi < 300s | ⏳ | ⏳ | ⏳ | — | — | — |
| **Bir xil `initData` qayta qabul qilindi** | ⏳ | ⏳ | ⏳ | — | — | — |
| `Origin` yetdi (POST) | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| `Referer` yetdi | ⏳ | ⏳ | ⏳ | sim: ✅ | — | — |
| Silent re-auth ishlaydi | ⏳ | ⏳ | ⏳ | — | — | — |

`sim:` = Chromium simulyatsiyasi natijasi, real klient emas (§4 chegaralari).
`—` = o'lchanmagan va o'lchash imkoni yo'q.

---

## 6. Dastlabki xulosalar

> Quyidagilar **Chromium'dagi dalilga asoslangan mulohazalar**, yakuniy xulosa emas. Native
> WebView (Android/iOS/Desktop) o'zining cookie do'koni, umri va tozalash siyosatiga ega —
> ular §5 dagi real test bilan o'lchanadi.

Fizik natijalarsiz ham simulyatsiya ikkita qarorni **qo'llab-quvvatlaydi**:

1. **D-13 dagi `Partitioned` atributi olib tashlanmasin.** Uchinchi tomon cookie'lari bloklangan
   Chromium'da faqat u cookie'ni saqlab qoladi.
2. **D-15 (silent re-auth) haqiqatan majburiy.** Safari uchinchi tomon cookie'larini butunlay
   bloklaydi va `Partitioned`ni qo'llab-quvvatlamaydi, ya'ni Telegram Web + Safari'da cookie
   **ishlamasligi kutiladi**. Agar cookie yagona mexanizm bo'lganida, bu foydalanuvchilar
   ilovaga umuman kira olmasdi. Invariant 16 shu holatni normal deb belgilaydi.

Fizik natijalar quyidagilarni o'zgartirishi mumkin va shuning uchun ular 1-bosqichdan **oldin**
kerak:

- Agar **qayta ochgandan keyin cookie omon qolmasa** (iOS WKWebView'da ehtimoli bor), D-14 dagi
  7 kunlik refresh sessiyasi amalda ishlamaydi va har ochilishda silent re-auth yagona yo'l
  bo'ladi — bu 1-bosqich kodini soddalashtiradi.
- Agar **`Origin`/`Referer` biror klientda yetmasa**, D-19 ning 3-qatlami o'sha muhitda
  o'chiriladi (asosiy CSRF token qatlami o'zgarishsiz qoladi).
- Agar **bir xil `initData` qayta qabul qilinmasa**, D-17 ning implementatsiyasida xato bor
  degani — legitim reload buziladi.

---

## 7. Diagnostika vositasining hayot sikli

| Fayl | Taqdiri |
|---|---|
| `backend/app/api/v1/diag.py` | 0-bosqich yopilgach **o'chiriladi** |
| `backend/app/api/v1/router.py` dagi `if settings.debug:` bloki | 0-bosqich yopilgach **o'chiriladi** |
| `frontend/public/_diag/webview.html` | 0-bosqich yopilgach **o'chiriladi** |
| `tools/webview-sim/` | Qoladi — regressiya tekshiruvi sifatida foydali |
| Ushbu hujjat | Qoladi — qaror asoslari yozuvi sifatida |

**Xavfsizlik kafolatlari (D: 5-talab):**
- Router **faqat `settings.debug` rost bo'lganda** ulanadi va `diag` moduli o'sha shart ichida
  import qilinadi — production jarayonida bu marshrutlar **umuman mavjud emas**.
- Endpointlar hech kimni tizimga kiritmaydi, token bermaydi, akkaunt yaratmaydi, bazaga
  tegmaydi.
- `telegram_id` va cookie qiymati maskalanadi; raw `initData` hech qayerda loglanmaydi (D-146).

**Vositaning o'z tekshiruvi** (`fastapi.testclient` bilan bajarildi, 22 ta tekshiruv, hammasi
o'tdi): Set-Cookie atributlari to'liq va `Domain` yo'q · maskalash ishlaydi · to'g'ri imzo
qabul qilinadi · **aynan bir xil `initData` qayta yuborilganda ham qabul qilinadi (D-17)** ·
buzilgan imzo rad etiladi · 1 soatlik `initData` 300s oynasidan tashqarida deb belgilanadi,
lekin imzosi hali ham to'g'ri (freshness va imzo alohida hisoblanadi) · `Origin`/`Referer`
qayd etiladi.

---

*0-bosqich §5 dagi uchta qurilma natijasi kelib, §5.3 matritsasi to'ldirilgandan keyin
yopiladi. 1-bosqich shundan keyin boshlanadi.*
