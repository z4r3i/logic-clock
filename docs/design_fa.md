<div dir="rtl">

# ساعت دیجیتال تمام‌سخت‌افزاری ۲۴ ساعته — سند طراحی کامل

> ناوبری: [راهنمای ساخت و تست](proteus_guide_fa.md) · [نت‌لیست](../netlist/netlist.csv) · [BOM](../netlist/bom.csv) · [برگه سیم‌کشی](../netlist/proteus_wiring.md) · [شرح نت‌ها](../netlist/nets.csv)

پایهٔ زمان: کریستال ۳۲٫۷۶۸ kHz + CD4060B + تقسیم بر ۲ با CD4013B
شمارش: شش عدد CD4026B (MOD-60 / MOD-60 / MOD-24) — بدون هیچ میکروکنترلر، برنامه یا FPGA
تغذیه: ۹–۱۲ V DC → 7805 → ۵ V
نمایش: شش نمایشگر ۷ سگمنت **کاتد مشترک** SC52-11EWA + کولن چشمک‌زن ۱ Hz

---

## ۰) وضعیت تأیید — صادقانه و مطابق قاعدهٔ الزامی

| بخش | روش تأیید | وضعیت |
|---|---|---|
| منطق شمارش، کری‌ها، مرزهای 60/60/24، تنظیم و ریست | شبیه‌سازی تابعی JS روی ۹۰۰۶۱ ثانیه (۲۵ ساعت) + تست مرزها | **تأیید شده** (`sim/verify.js`: ALL VERIFICATION PASSED) |
| فاز و فرکانس پایهٔ زمان (اولین لبه دقیقاً t=1.000s، سپس ۱ Hz) | شبیه‌سازی سیکل‌دقیق ۱۶۳۸۴۰ سیکل اسیلاتور | **تأیید شده** (`sim/divider_check.js`) |
| پین‌اوت‌ها و نام پایه‌ها | دیتاشیت رسمی سازنده (TI/Harris برای CMOS، ON Semi برای 7805، Kingbright برای نمایشگر) | **تأیید شده** (تصاویر رندرشده در `research/`) |
| عرض پالس ریست/کری در بدترین حالت | محاسبه از تأخیرهای typ/max دیتاشیت | **محاسبه‌شده**؛ حاشیه ≥ ۲٫۵ برابر |
| راه‌اندازی کریستال، شیب کند تغذیه، دیبانس آنالوگ، جریان LED | محاسبهٔ مداری | **محاسبه‌شده — نیازمند تأیید در Proteus/برد واقعی** |
| شبیه‌سازی کامل Proteus | — | **انجام نشده؛ این سند طراحی را «تأییدشدهٔ نهایی» اعلام نمی‌کند** |

طبق قاعدهٔ الزامی: هر جا شبیه‌سازی لازم است، صریحاًعلامت‌گذاری شده. روش‌های نامطمئن (دیکود ناهمگام روی شمارندهٔ سنکرون CD4518، دیود-لاجیک بدون تحلیل پلاریته) **رد** شده‌اند و دلیل رد در بخش ۱۶ آمده است.

---

## ۱) بلوک دیاگرام (۱۱ بلوک)

```
 [B1 تغذیه]  9-12V --D1--> 7805 --+5V(VCC)--> همهٔ بلوک‌ها
      |
 [B2 POR] R100k/C10u/1N4148 --> POR_RST --+
 [B10 کلیدها] 5x (100k+1uF+switch+CD4093) --+--> RST_GLOBAL = POR_RST + BTN_MSTRST
      |                                   |
      |   BTN_SET/HOUR/MIN/SECRST         v
 [B3 اسیلاتور+تقسیم] Y1 32.768k + CD4060(U1) --Q14=2Hz--> [B4 ÷2: CD4013 FF1] --CLK1HZ--+
      ^ RST_GLOBAL                                                                  |
      |                                                                             v
 [B5 کنترل SET] CD4013 FF2 (تاگل با BTN_SET) = SET_MODE --> nSET_MODE --> [B9a گیت کلاک]
                                                                                    |
 [B6 ثانیه MOD-60]  U3(SU) --C_SU--> U4(ST) --D6_ST(e.f.g)--+                          |
 [B7 دقیقه MOD-60]  U5(MU) --C_MU--> U6(MT) --D6_MT(e.f.g)--+                          |
 [B8 ساعت MOD-24]   U7(HU) --C_HU--> U8(HT) --D24(HT2.HU4)--+                          |
                                                           v                          v
 [B9 مسیر کری/ریست] U12,U13 (OR): RST_SEC/RST_ST/RST_MT/RST_HOURS و CLK_SEC/CLK_MU/CLK_HU
                                                           |
 [B11 نمایش] DS1..DS6 (CC) + 42x470R ؛ کولن: CLK1HZ -> 10k -> 2N3904 -> 2x LED+1k
```

جدول بلوک‌ها:

| بلوک | عملکرد | قطعات |
|---|---|---|
| B1 | تغذیهٔ ۵ V پایدار + حفاظت پلاریته | J1, D1, U16, C_IN1/2, C_OUT1/2, C_BULK, 15×C_BYP |
| B2 | ریست خودکار روشن‌شدن (~۰٫۸۷ s) | R_POR, C_POR, D2, U15/3 |
| B3 | اسیلاتور پیرس + تقسیم ۲^۱۴ | Y1, C1, C2, R_C, R_S, U1 |
| B4 | تقسیم بر ۲ دقیق → ۱ Hz | U2 (FF1), U15/4 |
| B5 | حالت تنظیم (تاگل) | U2 (FF2), U15/2, U11/3, U11/4 |
| B6 | ثانیه ۰۰–۵۹ | U3, U4, U9/1, U9/2 |
| B7 | دقیقه ۰۰–۵۹ | U5, U6, U9/3, U9/4 |
| B8 | ساعت ۰۰–۲۳ | U7, U8, U10/1..4, U11/1 |
| B9 | جمع‌کنندهٔ ریست/کری و گیت کلاک | U12, U13, U11/2 |
| B10 | دیبانس و شکل‌دهی ۵ کلید | SW×5, R_PU×5, C_BTN×5, U14, U15/1 |
| B11 | نمایش + کولن | DS1..DS6, 42×R, R_CB, R_CL1/2, Q1, LED1/2 |

---

## ۲) شرح عملکرد

۱. با اتصال تغذیه، B2 پایهٔ POR_N را نزدیک ۰ نگه می‌دارد؛ U15/3 آن را معکوس کرده POR_RST=1 می‌سازد؛ U13/1 خروجی RST_GLOBAL=1 می‌دهد. این سطح، تقسیم‌کنندهٔ U1، هر دو فلیپ‌فلاپ U2 و شمارنده‌های U3 و U5 را مستقیم و U4/U6/U7/U8 را از طریق ORهای U12 در ریست نگه می‌دارد → نمایش **00:00:00**.
۲. پس از ≈۰٫۸۷ ثانیه POR_N از آستانهٔ بالای اشمیت (≈۲٫۹ V) عبور می‌کند، POR_RST=0 و RST_GLOBAL=0 می‌شود. اسیلاتور از قبل روشن است؛ تقسیم‌کننده از صفر شروع می‌کند.
۳. Q14 = ۲ Hz. U15/4 آن را معکوس می‌کند و FF1 (با D=Q̄) روی لبهٔ بالاروندهٔ آن تاگل می‌کند. چون FF1 در دوران ریست با SET1=1 پیش‌تنظیم شده (Q1=1)، **اولین لبهٔ بالاروندهٔ CLK1HZ دقیقاً ۱٫۰۰۰ ثانیه پس از رهاسازی ریست** رخ می‌دهد و پس از آن هر ۱٫۰۰۰ ثانیه یک لبه (اثبات: `sim/divider_check.js`).
۴. CLK_SEC = CLK1HZ · nSET_MODE به کلاک U3 می‌رود. U3 هر ۱۰ لبه یک کری (C_SU، لبهٔ بالا در گذر ۹→۰) به U4 می‌دهد. وقتی U4 به ۶ می‌رسد، دیکود e·f·g پالسی می‌سازد که هم U4 را ریست می‌کند (MOD-6) و هم از طریق U13/2 یک لبهٔ کلاک به U5 می‌فرستد → دقیقه +۱. به این ترتیب ثانیه MOD-60 است.
۵. زنجیرهٔ دقیقه عیناً همان ساختار است (U5/U6 + D6_MT) و کری آن (D6_MT) کلاک U7 می‌شود.
۶. ساعت: U7 واحدها و U8 دهگان‌ها. D24 = (HT=2)·(HU=4) به محض رسیدن به ۲۴ هر دو را ریست می‌کند → 00. کری داخلی U7 (C_HU) کلاک U8 است.
۷. حالت تنظیم: فشار BTN_SET فلیپ‌فلاپ FF2 را تاگل می‌کند → SET_MODE=1. آنگاه CLK_SEC=0 (ثانیه یخ می‌زند)، HOUR_GATE=BTN_HOUR و MIN_GATE=BTN_MIN فعال می‌شوند و هر فشار = یک افزایش. SEC RESET در هر دو حالت ثانیه‌ها را صفر می‌کند. MASTER RESET همه‌چیز را صفر می‌کند. خروج از تنظیم با فشار دوبارهٔ SET.
۸. کولن: CLK1HZ بیس Q1 را از طریق ۱۰k می‌راند؛ دو LED کولن با ۱k از VCC تغذیه می‌شوند و با ۱ Hz چشمک می‌زنند.

---

## ۳) شماتیک کامل

شماتیک کامل و خوانا به سه شکل تحویل می‌شود که هر سه از **یک منبع واحد** (`netlist/gen_netlist.py`) تولید شده‌اند و بنابراین هیچ ناسازگاری بین آن‌ها ممکن نیست:

1. **`netlist/netlist.csv`** — جدول کامل «پین → نت» برای هر ۴۸۴ پین (همهٔ پایه‌های ICها، مقاومت‌ها، خازن‌ها، دیودها، کلیدها، نمایشگرها، کانکتور). هر اتصال = دو یا چند پین هم‌نت. این فایل مرجع بازسازی شماتیک در Proteus یا روی برد است.
2. **`visuals/schematic.html`** — شماتیک بلوکی تعاملی با نام همهٔ نت‌ها و شمارهٔ پایه‌ها (بخش ۶ همین سند را نیز ببینید).
3. **جدول‌های پایهٔ بخش ۴** — همان نتلیست به شکل جدول خوانا.

شماتیک‌های موضعیحیاتی (ASCII):

**اسیلاتور (مطابق Fig.13 دیتاشیت CD4060B):**
```
                 R_C 10M
   XTAL_A o------/\/\------o XTAL_B
      |         |            |
     --- C1    [Y1]         --- C2        U1 CD4060B:
     18p     32.768kHz      18p           pin11 = XTAL_A
      |         |            |            pin10 --/\/\-- XTAL_B  (R_S 220k)
     GND        |           GND           pin9  = NC
                |
   (کریستال و R_C بین A و B؛ C1 از A به GND؛ C2 از B به GND)
```
این دقیقاً توپولوژی Fig.13 دیتاشیت است: گرهٔ B فقط از طریق C2 به GND می‌رود و از طریق R_S به پایهٔ 10.

**POR:**
```
 VCC o--/\/\--o POR_N o----|<|----o VCC      (D2: آنود POR_N، کاتد VCC)
      100k    |         1N4148
             --- C_POR 10u
              |
             GND        POR_N --> U15 pins 8,9 --> pin10 = POR_RST
```

**دیبانس هر کلید (نمونه SET):**
```
 VCC o--/\/\--o BTN_SET_n o-----o U14 pins 1,2
      100k    |           |
             --- 1uF     [SW_SET]
              |           |
             GND         GND        U14 pin 3 = BTN_SET
```

**زنجیرهٔ کری/ریست ثانیه:**
```
 U3.5 (C_SU) ----> U4.1
 U4.11(e),U4.6(f) --> U9.1,2 → U9.3 = ST_EF
 ST_EF + U4.7(g) --> U9.5,6 → U9.4 = D6_ST
 D6_ST --> U12.8  (+ RST_SEC بر U12.9) → U12.10 = RST_ST → U4.15
 D6_ST --> U13.5  (+ MIN_GATE بر U13.6) → U13.4 = CLK_MU → U5.1
```

---

## ۴) جدول کامل پایه‌ها و اتصال‌ها

قواعد رعایت‌شده: هیچ ورودی شناور نیست؛ ورودی‌های گیت بلااستفاده به GND؛ پایه‌های NC صریحاًعلامت‌گذاری؛ RESET همهٔ CD4026/CD4060 **Active HIGH**؛ SET/RESET CD4013 **Active HIGH ناهمگام**؛ کلاک CD4013 و CD4026 **لبهٔ بالارونده** (CD4026 با CLOCK INHIBIT=0).

### ۴-۱) پایه‌های ICها و ترانزیستور/رگولاتور

| Ref | مدل | مقدار | پکیج | پین | نام پین | نت | توضیح |
|---|---|---|---|---|---|---|---|
| U1 | CD4060B | - | DIP-16 | 1 | Q12 | NC |  |
| U1 | CD4060B | - | DIP-16 | 2 | Q13 | NC |  |
| U1 | CD4060B | - | DIP-16 | 3 | Q14 | CLK2HZ |  |
| U1 | CD4060B | - | DIP-16 | 4 | Q6 | NC |  |
| U1 | CD4060B | - | DIP-16 | 5 | Q5 | NC |  |
| U1 | CD4060B | - | DIP-16 | 6 | Q7 | NC |  |
| U1 | CD4060B | - | DIP-16 | 7 | Q4 | NC |  |
| U1 | CD4060B | - | DIP-16 | 8 | VSS | GND |  |
| U1 | CD4060B | - | DIP-16 | 9 | OSC OUT (phi0) | NC | internal osc output; leave open per Fig.13 |
| U1 | CD4060B | - | DIP-16 | 10 | OSC OUT/ (phi0bar) | OSC_FB | to Rs then XTAL_B per Fig.13 |
| U1 | CD4060B | - | DIP-16 | 11 | OSC IN (phi1) | XTAL_A |  |
| U1 | CD4060B | - | DIP-16 | 12 | RESET | RST_GLOBAL | active HIGH |
| U1 | CD4060B | - | DIP-16 | 13 | Q9 | NC |  |
| U1 | CD4060B | - | DIP-16 | 14 | Q8 | NC |  |
| U1 | CD4060B | - | DIP-16 | 15 | Q10 | NC |  |
| U1 | CD4060B | - | DIP-16 | 16 | VDD | VCC |  |
| U2 | CD4013B | - | DIP-14 | 1 | Q1 | CLK1HZ |  |
| U2 | CD4013B | - | DIP-14 | 2 | Q1/ | FF1_D |  |
| U2 | CD4013B | - | DIP-14 | 3 | CLOCK1 | CLK2HZ_INV |  |
| U2 | CD4013B | - | DIP-14 | 4 | RESET1 | GND |  |
| U2 | CD4013B | - | DIP-14 | 5 | D1 | FF1_D |  |
| U2 | CD4013B | - | DIP-14 | 6 | SET1 | RST_GLOBAL | preset Q1=1 during reset => first 1Hz edge at t=1.000s |
| U2 | CD4013B | - | DIP-14 | 7 | VSS | GND |  |
| U2 | CD4013B | - | DIP-14 | 8 | SET2 | GND |  |
| U2 | CD4013B | - | DIP-14 | 9 | D2 | FF2_D |  |
| U2 | CD4013B | - | DIP-14 | 10 | RESET2 | RST_GLOBAL |  |
| U2 | CD4013B | - | DIP-14 | 11 | CLOCK2 | BTN_SET |  |
| U2 | CD4013B | - | DIP-14 | 12 | Q2/ | FF2_D |  |
| U2 | CD4013B | - | DIP-14 | 13 | Q2 | SET_MODE |  |
| U2 | CD4013B | - | DIP-14 | 14 | VDD | VCC |  |
| U3 | CD4026B | - | DIP-16 | 1 | CLOCK | CLK_SEC |  |
| U3 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U3 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U3 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U3 | CD4026B | - | DIP-16 | 5 | CARRY OUT | C_SU |  |
| U3 | CD4026B | - | DIP-16 | 10 | segment a | SEG_SU_A |  |
| U3 | CD4026B | - | DIP-16 | 12 | segment b | SEG_SU_B |  |
| U3 | CD4026B | - | DIP-16 | 13 | segment c | SEG_SU_C |  |
| U3 | CD4026B | - | DIP-16 | 9 | segment d | SEG_SU_D |  |
| U3 | CD4026B | - | DIP-16 | 11 | segment e | SEG_SU_E |  |
| U3 | CD4026B | - | DIP-16 | 6 | segment f | SEG_SU_F |  |
| U3 | CD4026B | - | DIP-16 | 7 | segment g | SEG_SU_G |  |
| U3 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U3 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U3 | CD4026B | - | DIP-16 | 15 | RESET | RST_SEC | active HIGH |
| U3 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U4 | CD4026B | - | DIP-16 | 1 | CLOCK | C_SU |  |
| U4 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U4 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U4 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U4 | CD4026B | - | DIP-16 | 5 | CARRY OUT | NC |  |
| U4 | CD4026B | - | DIP-16 | 10 | segment a | SEG_ST_A |  |
| U4 | CD4026B | - | DIP-16 | 12 | segment b | SEG_ST_B |  |
| U4 | CD4026B | - | DIP-16 | 13 | segment c | SEG_ST_C |  |
| U4 | CD4026B | - | DIP-16 | 9 | segment d | SEG_ST_D |  |
| U4 | CD4026B | - | DIP-16 | 11 | segment e | SEG_ST_E |  |
| U4 | CD4026B | - | DIP-16 | 6 | segment f | SEG_ST_F |  |
| U4 | CD4026B | - | DIP-16 | 7 | segment g | SEG_ST_G |  |
| U4 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U4 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U4 | CD4026B | - | DIP-16 | 15 | RESET | RST_ST | active HIGH |
| U4 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U5 | CD4026B | - | DIP-16 | 1 | CLOCK | CLK_MU |  |
| U5 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U5 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U5 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U5 | CD4026B | - | DIP-16 | 5 | CARRY OUT | C_MU |  |
| U5 | CD4026B | - | DIP-16 | 10 | segment a | SEG_MU_A |  |
| U5 | CD4026B | - | DIP-16 | 12 | segment b | SEG_MU_B |  |
| U5 | CD4026B | - | DIP-16 | 13 | segment c | SEG_MU_C |  |
| U5 | CD4026B | - | DIP-16 | 9 | segment d | SEG_MU_D |  |
| U5 | CD4026B | - | DIP-16 | 11 | segment e | SEG_MU_E |  |
| U5 | CD4026B | - | DIP-16 | 6 | segment f | SEG_MU_F |  |
| U5 | CD4026B | - | DIP-16 | 7 | segment g | SEG_MU_G |  |
| U5 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U5 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U5 | CD4026B | - | DIP-16 | 15 | RESET | RST_GLOBAL | active HIGH |
| U5 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U6 | CD4026B | - | DIP-16 | 1 | CLOCK | C_MU |  |
| U6 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U6 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U6 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U6 | CD4026B | - | DIP-16 | 5 | CARRY OUT | NC |  |
| U6 | CD4026B | - | DIP-16 | 10 | segment a | SEG_MT_A |  |
| U6 | CD4026B | - | DIP-16 | 12 | segment b | SEG_MT_B |  |
| U6 | CD4026B | - | DIP-16 | 13 | segment c | SEG_MT_C |  |
| U6 | CD4026B | - | DIP-16 | 9 | segment d | SEG_MT_D |  |
| U6 | CD4026B | - | DIP-16 | 11 | segment e | SEG_MT_E |  |
| U6 | CD4026B | - | DIP-16 | 6 | segment f | SEG_MT_F |  |
| U6 | CD4026B | - | DIP-16 | 7 | segment g | SEG_MT_G |  |
| U6 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U6 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U6 | CD4026B | - | DIP-16 | 15 | RESET | RST_MT | active HIGH |
| U6 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U7 | CD4026B | - | DIP-16 | 1 | CLOCK | CLK_HU |  |
| U7 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U7 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U7 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U7 | CD4026B | - | DIP-16 | 5 | CARRY OUT | C_HU |  |
| U7 | CD4026B | - | DIP-16 | 10 | segment a | SEG_HU_A |  |
| U7 | CD4026B | - | DIP-16 | 12 | segment b | SEG_HU_B |  |
| U7 | CD4026B | - | DIP-16 | 13 | segment c | SEG_HU_C |  |
| U7 | CD4026B | - | DIP-16 | 9 | segment d | SEG_HU_D |  |
| U7 | CD4026B | - | DIP-16 | 11 | segment e | SEG_HU_E |  |
| U7 | CD4026B | - | DIP-16 | 6 | segment f | SEG_HU_F |  |
| U7 | CD4026B | - | DIP-16 | 7 | segment g | SEG_HU_G |  |
| U7 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U7 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U7 | CD4026B | - | DIP-16 | 15 | RESET | RST_HOURS | active HIGH |
| U7 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U8 | CD4026B | - | DIP-16 | 1 | CLOCK | C_HU |  |
| U8 | CD4026B | - | DIP-16 | 2 | CLOCK INHIBIT | GND | tie LOW: count on CLOCK rising edge |
| U8 | CD4026B | - | DIP-16 | 3 | DISPLAY ENABLE IN | VCC | segments always on |
| U8 | CD4026B | - | DIP-16 | 4 | DISPLAY ENABLE OUT | NC |  |
| U8 | CD4026B | - | DIP-16 | 5 | CARRY OUT | NC |  |
| U8 | CD4026B | - | DIP-16 | 10 | segment a | SEG_HT_A |  |
| U8 | CD4026B | - | DIP-16 | 12 | segment b | SEG_HT_B |  |
| U8 | CD4026B | - | DIP-16 | 13 | segment c | SEG_HT_C |  |
| U8 | CD4026B | - | DIP-16 | 9 | segment d | SEG_HT_D |  |
| U8 | CD4026B | - | DIP-16 | 11 | segment e | SEG_HT_E |  |
| U8 | CD4026B | - | DIP-16 | 6 | segment f | SEG_HT_F |  |
| U8 | CD4026B | - | DIP-16 | 7 | segment g | SEG_HT_G |  |
| U8 | CD4026B | - | DIP-16 | 8 | VSS | GND |  |
| U8 | CD4026B | - | DIP-16 | 14 | UNGATED C | NC |  |
| U8 | CD4026B | - | DIP-16 | 15 | RESET | RST_HOURS | active HIGH |
| U8 | CD4026B | - | DIP-16 | 16 | VDD | VCC |  |
| U9 | CD4081B | - | DIP-14 | 1 | AND in A | SEG_ST_E |  |
| U9 | CD4081B | - | DIP-14 | 2 | AND in B | SEG_ST_F |  |
| U9 | CD4081B | - | DIP-14 | 3 | AND out Y | ST_EF |  |
| U9 | CD4081B | - | DIP-14 | 5 | AND in A | ST_EF |  |
| U9 | CD4081B | - | DIP-14 | 6 | AND in B | SEG_ST_G |  |
| U9 | CD4081B | - | DIP-14 | 4 | AND out Y | D6_ST |  |
| U9 | CD4081B | - | DIP-14 | 8 | AND in A | SEG_MT_E |  |
| U9 | CD4081B | - | DIP-14 | 9 | AND in B | SEG_MT_F |  |
| U9 | CD4081B | - | DIP-14 | 10 | AND out Y | MT_EF |  |
| U9 | CD4081B | - | DIP-14 | 12 | AND in A | MT_EF |  |
| U9 | CD4081B | - | DIP-14 | 13 | AND in B | SEG_MT_G |  |
| U9 | CD4081B | - | DIP-14 | 11 | AND out Y | D6_MT |  |
| U9 | CD4081B | - | DIP-14 | 7 | VSS | GND |  |
| U9 | CD4081B | - | DIP-14 | 14 | VDD | VCC |  |
| U10 | CD4081B | - | DIP-14 | 1 | AND in A | SEG_HT_A |  |
| U10 | CD4081B | - | DIP-14 | 2 | AND in B | SEG_HT_D |  |
| U10 | CD4081B | - | DIP-14 | 3 | AND out Y | HT_AD |  |
| U10 | CD4081B | - | DIP-14 | 5 | AND in A | HT_AD |  |
| U10 | CD4081B | - | DIP-14 | 6 | AND in B | SEG_HT_G |  |
| U10 | CD4081B | - | DIP-14 | 4 | AND out Y | HT2 |  |
| U10 | CD4081B | - | DIP-14 | 8 | AND in A | SEG_HU_C |  |
| U10 | CD4081B | - | DIP-14 | 9 | AND in B | SEG_HU_F |  |
| U10 | CD4081B | - | DIP-14 | 10 | AND out Y | HU_CF |  |
| U10 | CD4081B | - | DIP-14 | 12 | AND in A | HU_CF |  |
| U10 | CD4081B | - | DIP-14 | 13 | AND in B | SEG_HU_G |  |
| U10 | CD4081B | - | DIP-14 | 11 | AND out Y | HU4 |  |
| U10 | CD4081B | - | DIP-14 | 7 | VSS | GND |  |
| U10 | CD4081B | - | DIP-14 | 14 | VDD | VCC |  |
| U11 | CD4081B | - | DIP-14 | 1 | AND in A | HT2 |  |
| U11 | CD4081B | - | DIP-14 | 2 | AND in B | HU4 |  |
| U11 | CD4081B | - | DIP-14 | 3 | AND out Y | D24 |  |
| U11 | CD4081B | - | DIP-14 | 5 | AND in A | CLK1HZ |  |
| U11 | CD4081B | - | DIP-14 | 6 | AND in B | nSET_MODE |  |
| U11 | CD4081B | - | DIP-14 | 4 | AND out Y | CLK_SEC |  |
| U11 | CD4081B | - | DIP-14 | 8 | AND in A | BTN_HOUR |  |
| U11 | CD4081B | - | DIP-14 | 9 | AND in B | SET_MODE |  |
| U11 | CD4081B | - | DIP-14 | 10 | AND out Y | HOUR_GATE |  |
| U11 | CD4081B | - | DIP-14 | 12 | AND in A | BTN_MIN |  |
| U11 | CD4081B | - | DIP-14 | 13 | AND in B | SET_MODE |  |
| U11 | CD4081B | - | DIP-14 | 11 | AND out Y | MIN_GATE |  |
| U11 | CD4081B | - | DIP-14 | 7 | VSS | GND |  |
| U11 | CD4081B | - | DIP-14 | 14 | VDD | VCC |  |
| U12 | CD4071B | - | DIP-14 | 1 | OR in A | RST_GLOBAL |  |
| U12 | CD4071B | - | DIP-14 | 2 | OR in B | BTN_SECRST |  |
| U12 | CD4071B | - | DIP-14 | 3 | OR out Y | RST_SEC |  |
| U12 | CD4071B | - | DIP-14 | 5 | OR in A | RST_GLOBAL |  |
| U12 | CD4071B | - | DIP-14 | 6 | OR in B | D24 |  |
| U12 | CD4071B | - | DIP-14 | 4 | OR out Y | RST_HOURS |  |
| U12 | CD4071B | - | DIP-14 | 8 | OR in A | RST_SEC |  |
| U12 | CD4071B | - | DIP-14 | 9 | OR in B | D6_ST |  |
| U12 | CD4071B | - | DIP-14 | 10 | OR out Y | RST_ST |  |
| U12 | CD4071B | - | DIP-14 | 12 | OR in A | RST_GLOBAL |  |
| U12 | CD4071B | - | DIP-14 | 13 | OR in B | D6_MT |  |
| U12 | CD4071B | - | DIP-14 | 11 | OR out Y | RST_MT |  |
| U12 | CD4071B | - | DIP-14 | 7 | VSS | GND |  |
| U12 | CD4071B | - | DIP-14 | 14 | VDD | VCC |  |
| U13 | CD4071B | - | DIP-14 | 1 | OR in A | POR_RST |  |
| U13 | CD4071B | - | DIP-14 | 2 | OR in B | BTN_MSTRST |  |
| U13 | CD4071B | - | DIP-14 | 3 | OR out Y | RST_GLOBAL |  |
| U13 | CD4071B | - | DIP-14 | 5 | OR in A | D6_ST |  |
| U13 | CD4071B | - | DIP-14 | 6 | OR in B | MIN_GATE |  |
| U13 | CD4071B | - | DIP-14 | 4 | OR out Y | CLK_MU |  |
| U13 | CD4071B | - | DIP-14 | 8 | OR in A | D6_MT |  |
| U13 | CD4071B | - | DIP-14 | 9 | OR in B | HOUR_GATE |  |
| U13 | CD4071B | - | DIP-14 | 10 | OR out Y | CLK_HU |  |
| U13 | CD4071B | - | DIP-14 | 12 | OR in A | GND | unused gate: inputs tied LOW |
| U13 | CD4071B | - | DIP-14 | 13 | OR in B | GND | unused gate: inputs tied LOW |
| U13 | CD4071B | - | DIP-14 | 11 | OR out Y | NC | unused gate: inputs tied LOW |
| U13 | CD4071B | - | DIP-14 | 7 | VSS | GND |  |
| U13 | CD4071B | - | DIP-14 | 14 | VDD | VCC |  |
| U14 | CD4093B | - | DIP-14 | 1 | Schmitt NAND in A | BTN_SET_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 2 | Schmitt NAND in B | BTN_SET_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 3 | Schmitt NAND out Y | BTN_SET |  |
| U14 | CD4093B | - | DIP-14 | 5 | Schmitt NAND in A | BTN_HOUR_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 6 | Schmitt NAND in B | BTN_HOUR_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 4 | Schmitt NAND out Y | BTN_HOUR |  |
| U14 | CD4093B | - | DIP-14 | 8 | Schmitt NAND in A | BTN_MIN_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 9 | Schmitt NAND in B | BTN_MIN_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 10 | Schmitt NAND out Y | BTN_MIN |  |
| U14 | CD4093B | - | DIP-14 | 12 | Schmitt NAND in A | BTN_SECRST_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 13 | Schmitt NAND in B | BTN_SECRST_n | inputs tied => inverter |
| U14 | CD4093B | - | DIP-14 | 11 | Schmitt NAND out Y | BTN_SECRST |  |
| U14 | CD4093B | - | DIP-14 | 7 | VSS | GND |  |
| U14 | CD4093B | - | DIP-14 | 14 | VDD | VCC |  |
| U15 | CD4093B | - | DIP-14 | 1 | Schmitt NAND in A | BTN_MSTRST_n | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 2 | Schmitt NAND in B | BTN_MSTRST_n | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 3 | Schmitt NAND out Y | BTN_MSTRST |  |
| U15 | CD4093B | - | DIP-14 | 5 | Schmitt NAND in A | SET_MODE | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 6 | Schmitt NAND in B | SET_MODE | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 4 | Schmitt NAND out Y | nSET_MODE |  |
| U15 | CD4093B | - | DIP-14 | 8 | Schmitt NAND in A | POR_N | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 9 | Schmitt NAND in B | POR_N | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 10 | Schmitt NAND out Y | POR_RST |  |
| U15 | CD4093B | - | DIP-14 | 12 | Schmitt NAND in A | CLK2HZ | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 13 | Schmitt NAND in B | CLK2HZ | inputs tied => inverter |
| U15 | CD4093B | - | DIP-14 | 11 | Schmitt NAND out Y | CLK2HZ_INV |  |
| U15 | CD4093B | - | DIP-14 | 7 | VSS | GND |  |
| U15 | CD4093B | - | DIP-14 | 14 | VDD | VCC |  |
| U16 | MC7805/LM7805 | - | TO-220 | 1 | INPUT | VIN2 |  |
| U16 | MC7805/LM7805 | - | TO-220 | 2 | GROUND | GND | tab = pin 2 |
| U16 | MC7805/LM7805 | - | TO-220 | 3 | OUTPUT | VCC |  |
| Q1 | 2N3904 | - | TO-92 | 1 | E | GND |  |
| Q1 | 2N3904 | - | TO-92 | 2 | B | COLON_B |  |
| Q1 | 2N3904 | - | TO-92 | 3 | C | COLON_K |  |

### ۴-۲) قطعات پاسیو، نمایشگرها، کلیدها، تغذیه

| Ref | مدل | مقدار | پکیج | پین | نام پین | نت | توضیح |
|---|---|---|---|---|---|---|---|
| Y1 | crystal 32.768kHz | CL=12.5pF | HC-49/S or cylinder | 1 | - | XTAL_A |  |
| Y1 | crystal 32.768kHz | CL=12.5pF | HC-49/S or cylinder | 2 | - | XTAL_B |  |
| C1 | cap ceramic NP0 | 18pF | radial | 1 | - | XTAL_A |  |
| C1 | cap ceramic NP0 | 18pF | radial | 2 | - | GND |  |
| C2 | cap ceramic NP0 | 18pF | radial | 1 | - | XTAL_B |  |
| C2 | cap ceramic NP0 | 18pF | radial | 2 | - | GND |  |
| R_C | resistor | 10M | 0.25W | 1 | - | XTAL_A |  |
| R_C | resistor | 10M | 0.25W | 2 | - | XTAL_B |  |
| R_S | resistor | 220k | 0.25W | 1 | - | XTAL_B |  |
| R_S | resistor | 220k | 0.25W | 2 | - | OSC_FB |  |
| R_SUA | resistor | 470R | 0.25W | 1 | - | SEG_SU_A |  |
| R_SUA | resistor | 470R | 0.25W | 2 | - | DSP_SU_A |  |
| R_SUB | resistor | 470R | 0.25W | 1 | - | SEG_SU_B |  |
| R_SUB | resistor | 470R | 0.25W | 2 | - | DSP_SU_B |  |
| R_SUC | resistor | 470R | 0.25W | 1 | - | SEG_SU_C |  |
| R_SUC | resistor | 470R | 0.25W | 2 | - | DSP_SU_C |  |
| R_SUD | resistor | 470R | 0.25W | 1 | - | SEG_SU_D |  |
| R_SUD | resistor | 470R | 0.25W | 2 | - | DSP_SU_D |  |
| R_SUE | resistor | 470R | 0.25W | 1 | - | SEG_SU_E |  |
| R_SUE | resistor | 470R | 0.25W | 2 | - | DSP_SU_E |  |
| R_SUF | resistor | 470R | 0.25W | 1 | - | SEG_SU_F |  |
| R_SUF | resistor | 470R | 0.25W | 2 | - | DSP_SU_F |  |
| R_SUG | resistor | 470R | 0.25W | 1 | - | SEG_SU_G |  |
| R_SUG | resistor | 470R | 0.25W | 2 | - | DSP_SU_G |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_SU_A |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_SU_B |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_SU_C |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_SU_D |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_SU_E |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_SU_F |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_SU_G |  |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS6 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| R_STA | resistor | 470R | 0.25W | 1 | - | SEG_ST_A |  |
| R_STA | resistor | 470R | 0.25W | 2 | - | DSP_ST_A |  |
| R_STB | resistor | 470R | 0.25W | 1 | - | SEG_ST_B |  |
| R_STB | resistor | 470R | 0.25W | 2 | - | DSP_ST_B |  |
| R_STC | resistor | 470R | 0.25W | 1 | - | SEG_ST_C |  |
| R_STC | resistor | 470R | 0.25W | 2 | - | DSP_ST_C |  |
| R_STD | resistor | 470R | 0.25W | 1 | - | SEG_ST_D |  |
| R_STD | resistor | 470R | 0.25W | 2 | - | DSP_ST_D |  |
| R_STE | resistor | 470R | 0.25W | 1 | - | SEG_ST_E |  |
| R_STE | resistor | 470R | 0.25W | 2 | - | DSP_ST_E |  |
| R_STF | resistor | 470R | 0.25W | 1 | - | SEG_ST_F |  |
| R_STF | resistor | 470R | 0.25W | 2 | - | DSP_ST_F |  |
| R_STG | resistor | 470R | 0.25W | 1 | - | SEG_ST_G |  |
| R_STG | resistor | 470R | 0.25W | 2 | - | DSP_ST_G |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_ST_A |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_ST_B |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_ST_C |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_ST_D |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_ST_E |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_ST_F |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_ST_G |  |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS5 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| R_MUA | resistor | 470R | 0.25W | 1 | - | SEG_MU_A |  |
| R_MUA | resistor | 470R | 0.25W | 2 | - | DSP_MU_A |  |
| R_MUB | resistor | 470R | 0.25W | 1 | - | SEG_MU_B |  |
| R_MUB | resistor | 470R | 0.25W | 2 | - | DSP_MU_B |  |
| R_MUC | resistor | 470R | 0.25W | 1 | - | SEG_MU_C |  |
| R_MUC | resistor | 470R | 0.25W | 2 | - | DSP_MU_C |  |
| R_MUD | resistor | 470R | 0.25W | 1 | - | SEG_MU_D |  |
| R_MUD | resistor | 470R | 0.25W | 2 | - | DSP_MU_D |  |
| R_MUE | resistor | 470R | 0.25W | 1 | - | SEG_MU_E |  |
| R_MUE | resistor | 470R | 0.25W | 2 | - | DSP_MU_E |  |
| R_MUF | resistor | 470R | 0.25W | 1 | - | SEG_MU_F |  |
| R_MUF | resistor | 470R | 0.25W | 2 | - | DSP_MU_F |  |
| R_MUG | resistor | 470R | 0.25W | 1 | - | SEG_MU_G |  |
| R_MUG | resistor | 470R | 0.25W | 2 | - | DSP_MU_G |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_MU_A |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_MU_B |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_MU_C |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_MU_D |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_MU_E |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_MU_F |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_MU_G |  |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS4 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| R_MTA | resistor | 470R | 0.25W | 1 | - | SEG_MT_A |  |
| R_MTA | resistor | 470R | 0.25W | 2 | - | DSP_MT_A |  |
| R_MTB | resistor | 470R | 0.25W | 1 | - | SEG_MT_B |  |
| R_MTB | resistor | 470R | 0.25W | 2 | - | DSP_MT_B |  |
| R_MTC | resistor | 470R | 0.25W | 1 | - | SEG_MT_C |  |
| R_MTC | resistor | 470R | 0.25W | 2 | - | DSP_MT_C |  |
| R_MTD | resistor | 470R | 0.25W | 1 | - | SEG_MT_D |  |
| R_MTD | resistor | 470R | 0.25W | 2 | - | DSP_MT_D |  |
| R_MTE | resistor | 470R | 0.25W | 1 | - | SEG_MT_E |  |
| R_MTE | resistor | 470R | 0.25W | 2 | - | DSP_MT_E |  |
| R_MTF | resistor | 470R | 0.25W | 1 | - | SEG_MT_F |  |
| R_MTF | resistor | 470R | 0.25W | 2 | - | DSP_MT_F |  |
| R_MTG | resistor | 470R | 0.25W | 1 | - | SEG_MT_G |  |
| R_MTG | resistor | 470R | 0.25W | 2 | - | DSP_MT_G |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_MT_A |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_MT_B |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_MT_C |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_MT_D |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_MT_E |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_MT_F |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_MT_G |  |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS3 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| R_HUA | resistor | 470R | 0.25W | 1 | - | SEG_HU_A |  |
| R_HUA | resistor | 470R | 0.25W | 2 | - | DSP_HU_A |  |
| R_HUB | resistor | 470R | 0.25W | 1 | - | SEG_HU_B |  |
| R_HUB | resistor | 470R | 0.25W | 2 | - | DSP_HU_B |  |
| R_HUC | resistor | 470R | 0.25W | 1 | - | SEG_HU_C |  |
| R_HUC | resistor | 470R | 0.25W | 2 | - | DSP_HU_C |  |
| R_HUD | resistor | 470R | 0.25W | 1 | - | SEG_HU_D |  |
| R_HUD | resistor | 470R | 0.25W | 2 | - | DSP_HU_D |  |
| R_HUE | resistor | 470R | 0.25W | 1 | - | SEG_HU_E |  |
| R_HUE | resistor | 470R | 0.25W | 2 | - | DSP_HU_E |  |
| R_HUF | resistor | 470R | 0.25W | 1 | - | SEG_HU_F |  |
| R_HUF | resistor | 470R | 0.25W | 2 | - | DSP_HU_F |  |
| R_HUG | resistor | 470R | 0.25W | 1 | - | SEG_HU_G |  |
| R_HUG | resistor | 470R | 0.25W | 2 | - | DSP_HU_G |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_HU_A |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_HU_B |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_HU_C |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_HU_D |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_HU_E |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_HU_F |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_HU_G |  |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS2 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| R_HTA | resistor | 470R | 0.25W | 1 | - | SEG_HT_A |  |
| R_HTA | resistor | 470R | 0.25W | 2 | - | DSP_HT_A |  |
| R_HTB | resistor | 470R | 0.25W | 1 | - | SEG_HT_B |  |
| R_HTB | resistor | 470R | 0.25W | 2 | - | DSP_HT_B |  |
| R_HTC | resistor | 470R | 0.25W | 1 | - | SEG_HT_C |  |
| R_HTC | resistor | 470R | 0.25W | 2 | - | DSP_HT_C |  |
| R_HTD | resistor | 470R | 0.25W | 1 | - | SEG_HT_D |  |
| R_HTD | resistor | 470R | 0.25W | 2 | - | DSP_HT_D |  |
| R_HTE | resistor | 470R | 0.25W | 1 | - | SEG_HT_E |  |
| R_HTE | resistor | 470R | 0.25W | 2 | - | DSP_HT_E |  |
| R_HTF | resistor | 470R | 0.25W | 1 | - | SEG_HT_F |  |
| R_HTF | resistor | 470R | 0.25W | 2 | - | DSP_HT_F |  |
| R_HTG | resistor | 470R | 0.25W | 1 | - | SEG_HT_G |  |
| R_HTG | resistor | 470R | 0.25W | 2 | - | DSP_HT_G |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 7 | a | DSP_HT_A |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 6 | b | DSP_HT_B |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 4 | c | DSP_HT_C |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 2 | d | DSP_HT_D |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 1 | e | DSP_HT_E |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 9 | f | DSP_HT_F |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 10 | g | DSP_HT_G |  |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 3 | COM | GND | common cathode |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 8 | COM | GND | common cathode |
| DS1 | SC52-11EWA | CC red 0.52in | 10-pin | 5 | DP | NC |  |
| SW_SET | tact switch 6x6 | SPST-NO | 4-pin | 1 | - | BTN_SET_n | pins 1-2 joined |
| SW_SET | tact switch 6x6 | SPST-NO | 4-pin | 2 | - | BTN_SET_n | pins 1-2 joined |
| SW_SET | tact switch 6x6 | SPST-NO | 4-pin | 3 | - | GND | pins 3-4 joined |
| SW_SET | tact switch 6x6 | SPST-NO | 4-pin | 4 | - | GND | pins 3-4 joined |
| R_PU_SET | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_PU_SET | resistor | 100k | 0.25W | 2 | - | BTN_SET_n |  |
| C_BTN_SET | cap ceramic | 1uF | radial | 1 | - | BTN_SET_n |  |
| C_BTN_SET | cap ceramic | 1uF | radial | 2 | - | GND |  |
| SW_HOUR | tact switch 6x6 | SPST-NO | 4-pin | 1 | - | BTN_HOUR_n | pins 1-2 joined |
| SW_HOUR | tact switch 6x6 | SPST-NO | 4-pin | 2 | - | BTN_HOUR_n | pins 1-2 joined |
| SW_HOUR | tact switch 6x6 | SPST-NO | 4-pin | 3 | - | GND | pins 3-4 joined |
| SW_HOUR | tact switch 6x6 | SPST-NO | 4-pin | 4 | - | GND | pins 3-4 joined |
| R_PU_HOUR | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_PU_HOUR | resistor | 100k | 0.25W | 2 | - | BTN_HOUR_n |  |
| C_BTN_HOUR | cap ceramic | 1uF | radial | 1 | - | BTN_HOUR_n |  |
| C_BTN_HOUR | cap ceramic | 1uF | radial | 2 | - | GND |  |
| SW_MIN | tact switch 6x6 | SPST-NO | 4-pin | 1 | - | BTN_MIN_n | pins 1-2 joined |
| SW_MIN | tact switch 6x6 | SPST-NO | 4-pin | 2 | - | BTN_MIN_n | pins 1-2 joined |
| SW_MIN | tact switch 6x6 | SPST-NO | 4-pin | 3 | - | GND | pins 3-4 joined |
| SW_MIN | tact switch 6x6 | SPST-NO | 4-pin | 4 | - | GND | pins 3-4 joined |
| R_PU_MIN | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_PU_MIN | resistor | 100k | 0.25W | 2 | - | BTN_MIN_n |  |
| C_BTN_MIN | cap ceramic | 1uF | radial | 1 | - | BTN_MIN_n |  |
| C_BTN_MIN | cap ceramic | 1uF | radial | 2 | - | GND |  |
| SW_SECRST | tact switch 6x6 | SPST-NO | 4-pin | 1 | - | BTN_SECRST_n | pins 1-2 joined |
| SW_SECRST | tact switch 6x6 | SPST-NO | 4-pin | 2 | - | BTN_SECRST_n | pins 1-2 joined |
| SW_SECRST | tact switch 6x6 | SPST-NO | 4-pin | 3 | - | GND | pins 3-4 joined |
| SW_SECRST | tact switch 6x6 | SPST-NO | 4-pin | 4 | - | GND | pins 3-4 joined |
| R_PU_SECRST | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_PU_SECRST | resistor | 100k | 0.25W | 2 | - | BTN_SECRST_n |  |
| C_BTN_SECRST | cap ceramic | 1uF | radial | 1 | - | BTN_SECRST_n |  |
| C_BTN_SECRST | cap ceramic | 1uF | radial | 2 | - | GND |  |
| SW_MSTRST | tact switch 6x6 | SPST-NO | 4-pin | 1 | - | BTN_MSTRST_n | pins 1-2 joined |
| SW_MSTRST | tact switch 6x6 | SPST-NO | 4-pin | 2 | - | BTN_MSTRST_n | pins 1-2 joined |
| SW_MSTRST | tact switch 6x6 | SPST-NO | 4-pin | 3 | - | GND | pins 3-4 joined |
| SW_MSTRST | tact switch 6x6 | SPST-NO | 4-pin | 4 | - | GND | pins 3-4 joined |
| R_PU_MSTRST | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_PU_MSTRST | resistor | 100k | 0.25W | 2 | - | BTN_MSTRST_n |  |
| C_BTN_MSTRST | cap ceramic | 1uF | radial | 1 | - | BTN_MSTRST_n |  |
| C_BTN_MSTRST | cap ceramic | 1uF | radial | 2 | - | GND |  |
| R_POR | resistor | 100k | 0.25W | 1 | - | VCC |  |
| R_POR | resistor | 100k | 0.25W | 2 | - | POR_N |  |
| C_POR | cap electrolytic | 10uF | radial | 1 | + | POR_N |  |
| C_POR | cap electrolytic | 10uF | radial | 2 | - | GND |  |
| D2 | 1N4148 | - | DO-35 | 1 | A | POR_N | discharge on power-down |
| D2 | 1N4148 | - | DO-35 | 2 | K | VCC |  |
| R_CB | resistor | 10k | 0.25W | 1 | - | CLK1HZ |  |
| R_CB | resistor | 10k | 0.25W | 2 | - | COLON_B |  |
| R_CL1 | resistor | 1k | 0.25W | 1 | - | VCC |  |
| R_CL1 | resistor | 1k | 0.25W | 2 | - | COLON_A1 |  |
| R_CL2 | resistor | 1k | 0.25W | 1 | - | VCC |  |
| R_CL2 | resistor | 1k | 0.25W | 2 | - | COLON_A2 |  |
| LED1 | LED red | Vf~2.0V | 5mm | 1 | A | COLON_A1 |  |
| LED1 | LED red | Vf~2.0V | 5mm | 2 | K | COLON_K |  |
| LED2 | LED red | Vf~2.0V | 5mm | 1 | A | COLON_A2 |  |
| LED2 | LED red | Vf~2.0V | 5mm | 2 | K | COLON_K |  |
| J1 | DC jack / terminal | 9-12V in | 2-pin | 1 | + | VIN |  |
| J1 | DC jack / terminal | 9-12V in | 2-pin | 2 | - | GND |  |
| D1 | 1N4007 | - | DO-41 | 1 | A | VIN | reverse-polarity protection |
| D1 | 1N4007 | - | DO-41 | 2 | K | VIN2 |  |
| C_IN1 | cap ceramic/film | 0.33uF | radial | 1 | - | VIN2 |  |
| C_IN1 | cap ceramic/film | 0.33uF | radial | 2 | - | GND |  |
| C_IN2 | cap electrolytic | 100uF | radial | 1 | + | VIN2 |  |
| C_IN2 | cap electrolytic | 100uF | radial | 2 | - | GND |  |
| C_OUT1 | cap ceramic | 100nF | radial | 1 | - | VCC |  |
| C_OUT1 | cap ceramic | 100nF | radial | 2 | - | GND |  |
| C_OUT2 | cap electrolytic | 100uF | radial | 1 | + | VCC |  |
| C_OUT2 | cap electrolytic | 100uF | radial | 2 | - | GND |  |
| C_BULK | cap electrolytic | 470uF | radial | 1 | + | VCC |  |
| C_BULK | cap electrolytic | 470uF | radial | 2 | - | GND |  |
| C_BYP1 | cap ceramic | 100nF | radial | 1 | - | VCC | at U1 VDD |
| C_BYP1 | cap ceramic | 100nF | radial | 2 | - | GND | at U1 VSS |
| C_BYP2 | cap ceramic | 100nF | radial | 1 | - | VCC | at U2 VDD |
| C_BYP2 | cap ceramic | 100nF | radial | 2 | - | GND | at U2 VSS |
| C_BYP3 | cap ceramic | 100nF | radial | 1 | - | VCC | at U3 VDD |
| C_BYP3 | cap ceramic | 100nF | radial | 2 | - | GND | at U3 VSS |
| C_BYP4 | cap ceramic | 100nF | radial | 1 | - | VCC | at U4 VDD |
| C_BYP4 | cap ceramic | 100nF | radial | 2 | - | GND | at U4 VSS |
| C_BYP5 | cap ceramic | 100nF | radial | 1 | - | VCC | at U5 VDD |
| C_BYP5 | cap ceramic | 100nF | radial | 2 | - | GND | at U5 VSS |
| C_BYP6 | cap ceramic | 100nF | radial | 1 | - | VCC | at U6 VDD |
| C_BYP6 | cap ceramic | 100nF | radial | 2 | - | GND | at U6 VSS |
| C_BYP7 | cap ceramic | 100nF | radial | 1 | - | VCC | at U7 VDD |
| C_BYP7 | cap ceramic | 100nF | radial | 2 | - | GND | at U7 VSS |
| C_BYP8 | cap ceramic | 100nF | radial | 1 | - | VCC | at U8 VDD |
| C_BYP8 | cap ceramic | 100nF | radial | 2 | - | GND | at U8 VSS |
| C_BYP9 | cap ceramic | 100nF | radial | 1 | - | VCC | at U9 VDD |
| C_BYP9 | cap ceramic | 100nF | radial | 2 | - | GND | at U9 VSS |
| C_BYP10 | cap ceramic | 100nF | radial | 1 | - | VCC | at U10 VDD |
| C_BYP10 | cap ceramic | 100nF | radial | 2 | - | GND | at U10 VSS |
| C_BYP11 | cap ceramic | 100nF | radial | 1 | - | VCC | at U11 VDD |
| C_BYP11 | cap ceramic | 100nF | radial | 2 | - | GND | at U11 VSS |
| C_BYP12 | cap ceramic | 100nF | radial | 1 | - | VCC | at U12 VDD |
| C_BYP12 | cap ceramic | 100nF | radial | 2 | - | GND | at U12 VSS |
| C_BYP13 | cap ceramic | 100nF | radial | 1 | - | VCC | at U13 VDD |
| C_BYP13 | cap ceramic | 100nF | radial | 2 | - | GND | at U13 VSS |
| C_BYP14 | cap ceramic | 100nF | radial | 1 | - | VCC | at U14 VDD |
| C_BYP14 | cap ceramic | 100nF | radial | 2 | - | GND | at U14 VSS |
| C_BYP15 | cap ceramic | 100nF | radial | 1 | - | VCC | at U15 VDD |
| C_BYP15 | cap ceramic | 100nF | radial | 2 | - | GND | at U15 VSS |

### ۴-۳) فرهنگ نت‌ها

| نت | شرح |
|---|---|
| BTN_HOUR | debounced HOUR+ pulse |
| BTN_HOUR_n | raw HOUR+ node |
| BTN_MIN | debounced MIN+ pulse |
| BTN_MIN_n | raw MIN+ node |
| BTN_MSTRST | debounced master-reset pulse |
| BTN_MSTRST_n | raw MASTER RESET node |
| BTN_SECRST | debounced seconds-zero pulse |
| BTN_SECRST_n | raw SEC RESET node |
| BTN_SET | debounced SET pulse (active HIGH) |
| BTN_SET_n | raw SET node (pull-up + cap, LOW while pressed) |
| CLK1HZ | exact 1Hz, first rising edge t=1.000s after reset release |
| CLK2HZ | U1 Q14 = 2Hz |
| CLK2HZ_INV | inverted Q14 (U15/4) = clock of divide-by-2 FF |
| CLK_HU | D6_MT OR HOUR_GATE -> HU clock |
| CLK_MU | D6_ST OR MIN_GATE -> MU clock |
| CLK_SEC | CLK1HZ gated by nSET_MODE -> SU clock |
| COLON_A1 | LED1 anode via 1k |
| COLON_A2 | LED2 anode via 1k |
| COLON_B | Q1 base via 10k |
| COLON_K | colon LED cathodes = Q1 collector |
| C_HU | HU carry -> HT clock |
| C_MU | MU carry -> MT clock |
| C_SU | SU carry (1/10 Hz) -> ST clock |
| D24 | hour = 24 decode (HT2 AND HU4); reset pulse |
| D6_MT | minutes-tens = 6 decode (e.f.g); reset+carry pulse |
| D6_ST | seconds-tens = 6 decode (e.f.g); reset+carry pulse |
| DSP_HT_A | HT segment a (display side of 470R) |
| DSP_HT_B | HT segment b (display side of 470R) |
| DSP_HT_C | HT segment c (display side of 470R) |
| DSP_HT_D | HT segment d (display side of 470R) |
| DSP_HT_E | HT segment e (display side of 470R) |
| DSP_HT_F | HT segment f (display side of 470R) |
| DSP_HT_G | HT segment g (display side of 470R) |
| DSP_HU_A | HU segment a (display side of 470R) |
| DSP_HU_B | HU segment b (display side of 470R) |
| DSP_HU_C | HU segment c (display side of 470R) |
| DSP_HU_D | HU segment d (display side of 470R) |
| DSP_HU_E | HU segment e (display side of 470R) |
| DSP_HU_F | HU segment f (display side of 470R) |
| DSP_HU_G | HU segment g (display side of 470R) |
| DSP_MT_A | MT segment a (display side of 470R) |
| DSP_MT_B | MT segment b (display side of 470R) |
| DSP_MT_C | MT segment c (display side of 470R) |
| DSP_MT_D | MT segment d (display side of 470R) |
| DSP_MT_E | MT segment e (display side of 470R) |
| DSP_MT_F | MT segment f (display side of 470R) |
| DSP_MT_G | MT segment g (display side of 470R) |
| DSP_MU_A | MU segment a (display side of 470R) |
| DSP_MU_B | MU segment b (display side of 470R) |
| DSP_MU_C | MU segment c (display side of 470R) |
| DSP_MU_D | MU segment d (display side of 470R) |
| DSP_MU_E | MU segment e (display side of 470R) |
| DSP_MU_F | MU segment f (display side of 470R) |
| DSP_MU_G | MU segment g (display side of 470R) |
| DSP_ST_A | ST segment a (display side of 470R) |
| DSP_ST_B | ST segment b (display side of 470R) |
| DSP_ST_C | ST segment c (display side of 470R) |
| DSP_ST_D | ST segment d (display side of 470R) |
| DSP_ST_E | ST segment e (display side of 470R) |
| DSP_ST_F | ST segment f (display side of 470R) |
| DSP_ST_G | ST segment g (display side of 470R) |
| DSP_SU_A | SU segment a (display side of 470R) |
| DSP_SU_B | SU segment b (display side of 470R) |
| DSP_SU_C | SU segment c (display side of 470R) |
| DSP_SU_D | SU segment d (display side of 470R) |
| DSP_SU_E | SU segment e (display side of 470R) |
| DSP_SU_F | SU segment f (display side of 470R) |
| DSP_SU_G | SU segment g (display side of 470R) |
| FF1_D | U2 Q1/ tied to D1 (toggle) |
| FF2_D | U2 Q2/ tied to D2 (toggle) |
| GND | 0V common ground |
| HOUR_GATE | BTN_HOUR AND SET_MODE |
| HT2 | HT = 2 decode |
| HT_AD | HT a AND d |
| HU4 | HU = 4 decode |
| HU_CF | HU c AND f |
| MIN_GATE | BTN_MIN AND SET_MODE |
| MT_EF | MT e AND f |
| NC | not connected |
| OSC_FB | U1 pin 10 to Rs (osc feedback) |
| POR_N | power-on reset RC node (LOW at power-up) |
| POR_RST | POR pulse active HIGH ~0.87s |
| RST_GLOBAL | POR OR master reset; resets divider, FFs, SU, MU |
| RST_HOURS | RST_GLOBAL OR D24 -> HU+HT reset |
| RST_MT | RST_GLOBAL OR D6_MT -> MT reset |
| RST_SEC | RST_GLOBAL OR BTN_SECRST -> SU reset |
| RST_ST | RST_SEC OR D6_ST -> ST reset |
| SEG_HT_A | HT segment a (IC pin) |
| SEG_HT_B | HT segment b (IC pin) |
| SEG_HT_C | HT segment c (IC pin) |
| SEG_HT_D | HT segment d (IC pin) |
| SEG_HT_E | HT segment e (IC pin) |
| SEG_HT_F | HT segment f (IC pin) |
| SEG_HT_G | HT segment g (IC pin) |
| SEG_HU_A | HU segment a (IC pin) |
| SEG_HU_B | HU segment b (IC pin) |
| SEG_HU_C | HU segment c (IC pin) |
| SEG_HU_D | HU segment d (IC pin) |
| SEG_HU_E | HU segment e (IC pin) |
| SEG_HU_F | HU segment f (IC pin) |
| SEG_HU_G | HU segment g (IC pin) |
| SEG_MT_A | MT segment a (IC pin) |
| SEG_MT_B | MT segment b (IC pin) |
| SEG_MT_C | MT segment c (IC pin) |
| SEG_MT_D | MT segment d (IC pin) |
| SEG_MT_E | MT segment e (IC pin) |
| SEG_MT_F | MT segment f (IC pin) |
| SEG_MT_G | MT segment g (IC pin) |
| SEG_MU_A | MU segment a (IC pin) |
| SEG_MU_B | MU segment b (IC pin) |
| SEG_MU_C | MU segment c (IC pin) |
| SEG_MU_D | MU segment d (IC pin) |
| SEG_MU_E | MU segment e (IC pin) |
| SEG_MU_F | MU segment f (IC pin) |
| SEG_MU_G | MU segment g (IC pin) |
| SEG_ST_A | ST segment a (IC pin) |
| SEG_ST_B | ST segment b (IC pin) |
| SEG_ST_C | ST segment c (IC pin) |
| SEG_ST_D | ST segment d (IC pin) |
| SEG_ST_E | ST segment e (IC pin) |
| SEG_ST_F | ST segment f (IC pin) |
| SEG_ST_G | ST segment g (IC pin) |
| SEG_SU_A | SU segment a (IC pin) |
| SEG_SU_B | SU segment b (IC pin) |
| SEG_SU_C | SU segment c (IC pin) |
| SEG_SU_D | SU segment d (IC pin) |
| SEG_SU_E | SU segment e (IC pin) |
| SEG_SU_F | SU segment f (IC pin) |
| SEG_SU_G | SU segment g (IC pin) |
| SET_MODE | 1 = set mode (U2 Q2) |
| ST_EF | ST e AND f |
| VCC | +5V regulated rail |
| VIN | raw 9-12V input at connector |
| VIN2 | after reverse-protection diode D1, regulator input |
| XTAL_A | crystal node A = U1 pin 11 (osc in) |
| XTAL_B | crystal node B = C2/Rc/Rs junction |
| nSET_MODE | inverted SET_MODE |

---

## ۵) جدول منطق شمارنده‌ها

| گروه | یکان | دهگان | مدول کل | دیکود ریست | نت ریست | منبع کری به گروه بعد |
|---|---|---|---|---|---|---|
| ثانیه | U3 MOD-10 طبیعی | U4 MOD-6 با ریست در ۶ | ۶۰ | D6_ST = e·f·g | RST_ST = RST_SEC + D6_ST | D6_ST (پالس ریست = کری) |
| دقیقه | U5 MOD-10 طبیعی | U6 MOD-6 با ریست در ۶ | ۶۰ | D6_MT = e·f·g | RST_MT = RST_GLOBAL + D6_MT | D6_MT |
| ساعت | U7 MOD-10 مشروط | U8 فقط ۰/۱/۲ | ۲۴ | D24 = HT2·HU4 | RST_HOURS = RST_GLOBAL + D24 | — (آخرین گروه) |

رفتار لبه‌ها:

| گذر | لبهٔ کلاک ورودی | اثر | کری خروجی |
|---|---|---|---|
| SU 9→0 | CLK1HZ ↑ | SU=0 | C_SU ↑ (U4 +۱) |
| ST 5→6 | C_SU ↑ | ST=6 موقت → D6_ST=1 → ریست → ST=0 | D6_ST ↑ (U5 +۱) |
| MU 9→0 | CLK_MU ↑ | MU=0 | C_MU ↑ (U6 +۱) |
| MT 5→6 | C_MU ↑ | MT=6 موقت → ریست → 0 | D6_MT ↑ (U7 +۱) |
| HU 9→0 (HT<2) | CLK_HU ↑ | HU=0 | C_HU ↑ (U8 +۱) |
| HU 3→4 با HT=2 | CLK_HU ↑ | HU=4 موقت → D24=1 → HU,HT ریست → 00 | — |

نکتهٔ حالت‌های میانی: حالت «۶» در دهگان‌ها و «۲۴» در ساعت فقط چند صد نانوثانیه وجود دارد (پهنای پالس ریست، بخش ۷). چون CD4026 شمارندهٔ **جانسون** است، هر گذر فقط یک بیت داخلی را عوض می‌کند و دیکودهای استفاده‌شده روی مسیر رسیدن به حالت هدف **مونوتونیک** هستند (تحلیل گلیچ در بخش ۷-۳).

---

## ۶) جدول صحت دیکود + معادلات بولی + تعداد گیت

الگوی سگمنت‌های CD4026 (دیتاشیت):

| رقم | a | b | c | d | e | f | g | e·f·g | a·d·g | c·f·g |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | 1 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | **1** | 0 |
| 3 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| 4 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | **1** |
| 5 | 1 | 0 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 |
| 6 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | **1** | 0 | 0 |
| 7 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 9 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 1 | 1 |

**چرا یکتایی برقرار است (تحلیل دسترس‌پذیری):**
- `e·f·g` روی ارقام ۶ و ۸ درست است؛ اما دهگان‌های ثانیه/دقیقه هرگز به ۸ نمی‌رسند (در ۶ ریست می‌شوند) → یکتا روی مجموعهٔ دسترس‌پذیر {0..6}.
- `a·d·g` روی {2,6,8,9} درست است؛ دهگان ساعت فقط {0,1,2} را می‌بیند → یکتا.
- `c·f·g` روی {4,8,9} درست است؛ یکان ساعت وقتی دهگان=2 است فقط {0..4} را می‌بیند (در ۴ ریست می‌شود)؛ وقتی دهگان≠2 است HT2=0 و D24 خاموش می‌ماند → یکتا.
این یکتایی در `sim/verify.js` به‌صورت assert روی همهٔ حالت‌های دسترس‌پذیر بررسی شده است.

**معادلات و تخصیص گیت (شمارهٔ پایه دقیق):**

| معادله | گیت | پایه‌های ورودی→خروجی |
|---|---|---|
| ST_EF = SEG_ST_E·SEG_ST_F | U9/1 | 1,2→3 |
| D6_ST = ST_EF·SEG_ST_G | U9/2 | 5,6→4 |
| MT_EF = SEG_MT_E·SEG_MT_F | U9/3 | 8,9→10 |
| D6_MT = MT_EF·SEG_MT_G | U9/4 | 12,13→11 |
| HT_AD = SEG_HT_A·SEG_HT_D | U10/1 | 1,2→3 |
| HT2 = HT_AD·SEG_HT_G | U10/2 | 5,6→4 |
| HU_CF = SEG_HU_C·SEG_HU_F | U10/3 | 8,9→10 |
| HU4 = HU_CF·SEG_HU_G | U10/4 | 12,13→11 |
| D24 = HT2·HU4 | U11/1 | 1,2→3 |
| CLK_SEC = CLK1HZ·nSET_MODE | U11/2 | 5,6→4 |
| HOUR_GATE = BTN_HOUR·SET_MODE | U11/3 | 8,9→10 |
| MIN_GATE = BTN_MIN·SET_MODE | U11/4 | 12,13→11 |
| RST_SEC = RST_GLOBAL+BTN_SECRST | U12/1 | 1,2→3 |
| RST_HOURS = RST_GLOBAL+D24 | U12/2 | 5,6→4 |
| RST_ST = RST_SEC+D6_ST | U12/3 | 8,9→10 |
| RST_MT = RST_GLOBAL+D6_MT | U12/4 | 12,13→11 |
| RST_GLOBAL = POR_RST+BTN_MSTRST | U13/1 | 1,2→3 |
| CLK_MU = D6_ST+MIN_GATE | U13/2 | 5,6→4 |
| CLK_HU = D6_MT+HOUR_GATE | U13/3 | 8,9→10 |
| (بلااستفاده) | U13/4 | 12,13→11 (ورودی‌ها GND) |
| BTN_SET = /BTN_SET_n | U14/1 | 1,2→3 |
| BTN_HOUR = /BTN_HOUR_n | U14/2 | 5,6→4 |
| BTN_MIN = /BTN_MIN_n | U14/3 | 8,9→10 |
| BTN_SECRST = /BTN_SECRST_n | U14/4 | 12,13→11 |
| BTN_MSTRST = /BTN_MSTRST_n | U15/1 | 1,2→3 |
| nSET_MODE = /SET_MODE | U15/2 | 5,6→4 |
| POR_RST = /POR_N | U15/3 | 8,9→10 |
| CLK2HZ_INV = /CLK2HZ | U15/4 | 12,13→11 |

منابع سیگنال‌های سگمنتی: SEG_ST_E=U4.11، SEG_ST_F=U4.6، SEG_ST_G=U4.7؛ SEG_MT_E=U6.11، SEG_MT_F=U6.6، SEG_MT_G=U6.7؛ SEG_HT_A=U8.10، SEG_HT_D=U8.9، SEG_HT_G=U8.7؛ SEG_HU_C=U7.13، SEG_HU_F=U7.6، SEG_HU_G=U7.7.

**شمارش گیت:** AND = ۱۲ (۳× CD4081 کاملاً پر)؛ OR = ۷ استفاده + ۱ رزرو (۲× CD4071)؛ NAND اشمیت = ۸ (۲× CD4093 کاملاً پر). هیچ خروجی گیت به خروجی گیت دیگر وصل نیست؛ همهٔ جمع‌ها با OR انجام شده (نه wire-OR).

---

## ۷) مدار Carry و Reset + تحلیل پهنای پالس و تأخیر مشترک

### ۷-۱) کری‌های مستقیم
C_SU (U3.5)→U4.1، C_MU (U5.5)→U6.1، C_HU (U7.5)→U8.1. این‌ها خروجی CARRY خود CD4026 هستند: موج مربعی با فرکانس کلاک÷۱۰ و **لبهٔ بالارونده دقیقاً در گذر ۹→۰**. پهنای سطح بالا = ۵سیکل کلاک ورودی (برای C_SU: پنج ثانیه) ≫ حداقل ۲۲۰ ns. هیچ گیت اضافه‌ای در مسیر نیست → بدون گلیچ.

### ۷-۲) پالس خودریست = کری (MOD-6 و MOD-24)
زنجیرهٔ D6_ST: رسیدن به ۶ → e,f,g=1 → D6_ST ↑ → دو شاخه:
- شاخهٔ ریست: U12/3 (OR) → RST_ST → U4.15
- شاخهٔ کری: U13/2 (OR) → CLK_MU → U5.1

پهنای پالس روی گرهٔ D6_ST (= پهنای دیده‌شده توسط کلاک U5، چون OR تأخیر برابر به هر دو لبه می‌دهد):
`W_carry = t_OR(rise) + t_RESET→DECODE + 2·t_AND(fall)`
- typ @5V: 125 + 300 + 2×125 = **675 ns**
- max (کندترین گوشه): 250 + 600 + 2×250 = **1350 ns**
- گوشهٔ سریع (تأخیرها ≈۰٫۴×typ، تخمین محافظه‌کارانه چون دیتاشیت min نمی‌دهد): ≈۲۷۰ ns

پهنای پالس ریست روی پایهٔ U4.15: `W_reset = t_RESET→DECODE + 2·t_AND(fall)` = typ **550 ns**، max 1100 ns، گوشهٔ سریع ≈۲۲۰ ns.

حداقل‌های تضمینی دیتاشیت CD4026 @5V: کلاک ≥ **220 ns**، ریست ≥ **120 ns** (ستون max جدول AC = حداقل قابل قبول تضمینی). حاشیه: typ کری 675/220 ≈ ۳٫۱×؛ typ ریست 550/120 ≈ ۴٫۶×؛ حتی گوشهٔ سریع تخمینی ۲۷۰≥220 و ۲۲۰≥120. **بدون نیاز به one-shot**؛ با این حال اگر برد واقعی در گوشهٔ سریع/دمای بالا حاشیه را کم کرد، جایگزین معتبر: CD4538 به‌صورت monostable با پهنای ۱ µs روی مسیر کری (در BOM نیامده چون لازم نیست؛ روش اعلام‌شده و پشتیبان).

D24: `W = t_OR + t_RESET→DECODE + 3·t_AND` = typ 125+300+375 = **800 ns** (max 1600). فقط ریست است (کری به گروه بعد ندارد).

### ۷-۳) تحلیل گلیچ و اشتراک Reset/Carry
- fan-out گرهٔ D6_ST فقط **ورودی** دو گیت است (امپدانس بالا) → contention ندارد.
- U5 روی لبهٔ **بالاروندهٔ** D6_ST می‌شمارد؛ لبهٔ پایین‌رونده (پس از ریست U4) برای U5 بی‌اثر است → دقیقاً یک افزایش.
- ریست U4 تنها سگمنت g را خاموش می‌کند (۶→۰: فقط g تغییر می‌کند) → D6_ST مونوتونیک پایین می‌رود؛ پالس دوم تولید نمی‌شود.
- گذر ۵→۶ تنها سگمنت e را روشن می‌کند (f,g از قبل ۱) → D6_ST مونوتونیک بالا می‌رود؛ گلیچ پیش از ۶ ناممکن.
- گذرهای HT (1→2) و HU (3→4) چند سگمنت را عوض می‌کنند اما همهٔ تغییرات **هم‌جهت** (صعودی برای رسیدن به حالت دیکود) هستند → خروجی AND فقط وقتی بالا می‌رود که آخرین سگمنت بنشیند؛ گلیچ کاذب ندارد.
- اشتراک RST_GLOBAL با مسیرهای کری: RST_GLOBAL فقط به **ورودی** ORها و پایه‌های RESET می‌رود؛ هیچ‌جا با کری هم‌گره نیست مگر داخل OR که جمع منطقی ایمن است.
- رهاسازی ریست روشن‌شدن: U3/U5 اول آزاد می‌شوند؛ U4/U6/U7/U8 دو تأخیر OR دیرتر (~۲۵۰ ns). در این پنجره هیچ لبهٔ کلاکی وجود ندارد (اولین لبهٔ CLK1HZ در t=1s؛ C_SU در ریست سطح ۱ ثابت) → شمارش کاذب صفر.

---

## ۸) مدار Power-On Reset

اجزا: R_POR=100k (VCC→POR_N)، C_POR=10µF (POR_N→GND)، D2=1N4148 (آنود POR_N، کاتد VCC)، اینورتر اشمیت U15/3.
- سطح فعال: POR_RST **Active HIGH**؛ RST_GLOBAL Active HIGH.
- مدت: `t = −RC·ln(1−V_T+/VCC) = −(100k·10µ)·ln(1−2.9/5) ≈ 0.87 s` (V_T+ اشمیت CD4093 @5V ≈ ۲٫۹ V typ، هیسترزیس ≈۰٫۹ V).
- مسیر تخلیه: هنگام قطع تغذیه، VCC می‌افتد؛ به‌محض `VCC < POR_N − 0.6` دیود D2 رسانا شده خازن را به rail تخلیه می‌کند → مدار برای روشن‌شدن بعدی در < ~50 ms مسلح می‌شود (تست power-cycle).
- شیب کند تغذیه: RC=1s ≫ زمان ramp (مثلاً 100 ms) → POR_N تا پایدارشدن rail زیر آستانه می‌ماند و پالس کامل پس از پایداری ادامه می‌یابد؛ ریست ناقص رخ نمی‌دهد.
- این پالس همهٔ شمارنده‌ها + تقسیم‌کننده + فلیپ‌فلاپ‌ها را صفر می‌کند (بخش ۲) → شروع تعریف‌شده 00:00:00.

---

## ۹) مدار کلیدها و دیبانس

پنج کلید: SET، HOUR+، MIN+، SEC RESET، MASTER RESET. هر کدام: بالاکش ۱۰۰k به VCC، خازن ۱µF به GND، کلید به GND، و اینورتر اشمیت CD4093 (پایه‌ها در جدول بخش ۶).
- فشار: گرهٔ raw در چند µs تخلیه می‌شود → خروجی اشمیت یک لبهٔ تمیز بالا می‌دهد. بانس‌های حین بسته‌شدن: خازن گره را پایین نگه می‌دارد؛ شارژ مجدد در فاصله‌های بازِ بانس (≤۵ ms هر کدام) فقط ≈۰٫۲۵ V بالا می‌آورد ≪ V_T−≈2.0 V → **ثبت چندگانه ناممکن**.
- رها: شارژ با τ=100k·1µ=100 ms؛ عبور از V_T+ در ≈۸۷ ms؛ بانس‌های رها هر بار تخلیهٔ سریع → یک لبهٔ پایین تمیز پس از آخرین جدایش +۸۷ ms.
- پهنای پالس = مدت فشار + ۸۷ ms ≫ حداقل کلاک CD4013/CD4026 (مرتبهٔ ns).
- رفتار نگه‌داشتن: چون همهٔ مصرف‌کننده‌ها لبه‌محور هستند، نگه‌داشتن = **یک** افزایش/یک تاگل (تکرار خودکار ندارد — مطابق اختیار spec).
- SET: تاگل FF2؛ در حالت SET ثانیه یخ می‌زند (CLK_SEC=0)، HOUR+/MIN+ فعال؛ در حالت عادی HOUR+/MIN+ بی‌اثر (خروجی AND=0) → **بدون اختلال در شمارش عادی**.
- SEC RESET: RST_SEC = RST_GLOBAL + BTN_SECRST → هم U3 و هم U4 (از طریق RST_ST) صفر می‌شوند.
- MASTER RESET: RST_GLOBAL → صفر کردن همه‌چیز + پیش‌تنظیم FF1 → شروع تمیز با اولین لبه در t=1s.
- نکتهٔ رفتاری اعلام‌شده: در حالت SET اگر دقیقه با MIN+ از ۵۹ به ۰۰ برود، کری آبشاری D6_MT ساعت را نیز +۱ می‌کند (رفتار طبیعی زنجیرهٔ شمارنده؛ قطعی و بدون گلیچ). کاربر می‌تواند ساعت را با HOUR+ اصلاح کند.

---

## ۱۰) مدار تغذیه

```
 J1(9-12V) --D1 1N4007--> VIN2 -- U16.1 [7805] U16.3 --> VCC=5V
 VIN2: C_IN1 0.33u + C_IN2 100u به GND      VCC: C_OUT1 100n + C_OUT2 100u + C_BULK 470u
 U16.2 = GND (tab نیز pin2)                 15x C_BYP 100n چسبیده به VDD/VSS هر IC منطقی
```
- خازن‌های ورودی/خروجی مطابق دیتاشیت 7805 (Cin≥0.33µ، Co≥0.1µ)؛ الکترولیت‌ها برای میرایی transients.
- حفاظت پلاریته معکوس: D1 سری؛ در اتصال معکوس هیچ جریانی عبور نمی‌کند.
- اضافه‌ولتاژ: محدودهٔ کاری اعلام‌شده ۹–۱۲ V؛ abs max رگولاتور ۳۵ V است اما تلفات حرارتی رشد می‌کند (مثال ۲۴ V در بخش ۱۲) → برای ورودی >۱۲ V این طراحی **بدون هیت‌سینک معتبر نیست** (صریحاً اعلام می‌شود).
- حداقل ورودی در کانکتور: `5 + 2(dropout) + 0.7(D1) = 7.7 V` → حاشیهٔ خوب تا ۹ V.
- زمین مشترک: GND تک‌ستاره‌ای؛ همهٔ خازن‌ها و COM نمایشگرها به همان صفحهٔ زمین.

---

## ۱۱) BOM کامل

| # | Ref | نام قطعه | مدل | مقدار | تعداد | پکیج | توضیحات |
|---|---|---|---|---|---|---|---|
| 1 | U1 | شمارنده/تقسیم‌کننده ۱۴ مرحله با اسیلاتور | CD4060B | - | 1 | DIP-16 | منبع زمان؛ Q14=2Hz |
| 2 | U2 | فلیپ‌فلاپ D دوگانه | CD4013B | - | 1 | DIP-14 | FF1 تقسیم بر ۲؛ FF2 تاگل حالت SET |
| 3 | U3-U8 | شمارنده دهدهی + درایور ۷ سگمنت | CD4026B | - | 6 | DIP-16 | SU,ST,MU,MT,HU,HT |
| 4 | U9-U11 | چهار گیت AND دو ورودی | CD4081B | - | 3 | DIP-14 | دیکود 6/6/24 و گیت‌های کلاک |
| 5 | U12-U13 | چهار گیت OR دو ورودی | CD4071B | - | 2 | DIP-14 | جمع ریست/کری؛ یک گیت U13 بلااستفاده |
| 6 | U14-U15 | چهار NAND اشمیت تریگر | CD4093B | - | 2 | DIP-14 | دیبانس کلیدها، اینورترها، POR |
| 7 | U16 | رگولاتور ۵ ولت | MC7805/LM7805 | - | 1 | TO-220 | بدون هیت‌سینک؛ P≈0.44W max |
| 8 | Q1 | ترانزیستور NPN | 2N3904 | - | 1 | TO-92 | درایور چشمک‌زن کولن |
| 9 | DS1-DS6 | نمایشگر ۷ سگمنت کاتد مشترک | SC52-11EWA | قرمز 0.52in | 6 | 10-pin | COM=3,8؛ a=7,b=6,c=4,d=2,e=1,f=9,g=10,DP=5 |
| 10 | Y1 | کریستال ساعت | 32.768kHz | CL=12.5pF | 1 | HC-49S | با C1=C2=18pF و Cstray≈3.5pF |
| 11 | R_SA..R_SUG | مقاومت محدودکننده سگمنت | 470R | 0.25W | 42 | AXIAL | یک عدد برای هر سگمنت؛ I≈1.5mA |
| 12 | R_CL1,R_CL2 | مقاومت LED کولن | 1k | 0.25W | 2 | AXIAL | I≈2.8mA هر LED |
| 13 | R_CB | مقاومت بیس Q1 | 10k | 0.25W | 1 | AXIAL | IB≈0.43mA؛ اشباع عمیق |
| 14 | R_PU_SET..R_PU_MSTRST,R_POR | مقاومت بالاکش | 100k | 0.25W | 6 | AXIAL | ۵ کلید + مدار POR |
| 15 | R_S | مقاومت محدودکننده جریان کریستال | 220k | 0.25W | 1 | AXIAL | Fig.13 دیتاشیت CD4060 |
| 16 | R_C | مقاومت بایاس اسیلاتور | 10M | 0.25W | 1 | AXIAL | Fig.13 دیتاشیت CD4060 |
| 17 | C1,C2 | خازن بار کریستال | 18pF | NP0 | 2 | RADIAL | CL=(18*18)/(36)+3.5=12.5pF |
| 18 | C_BTN_SET..C_BTN_MSTRST | خازن دیبانس کلید | 1uF | X7R | 5 | RADIAL | با 100k و اشمیت CD4093 |
| 19 | C_POR | خازن ریست روشن‌شدن | 10uF | 16V | 1 | RADIAL | پالس ریست ≈0.87s |
| 20 | D2 | دیود تخلیه POR | 1N4148 | - | 1 | DO-35 | آند=POR_N، کاتد=VCC |
| 21 | D1 | دیود حفاظت پلاریته معکوس | 1N4007 | - | 1 | DO-41 | سری با ورودی تغذیه |
| 22 | C_IN1 | خازن ورودی رگولاتور | 0.33uF | film/ceramic | 1 | RADIAL | مطابق دیتاشیت 7805 |
| 23 | C_IN2 | خازن الکترولیت ورودی | 100uF | 25V | 1 | RADIAL | نزدیک پایه ۱ U16 |
| 24 | C_OUT1 | خازن خروجی رگولاتور | 100nF | ceramic | 1 | RADIAL | پایدارسازی 7805 |
| 25 | C_OUT2 | خازن الکترولیت خروجی | 100uF | 16V | 1 | RADIAL | نزدیک پایه ۳ U16 |
| 26 | C_BULK | خازن ذخیره برد | 470uF | 16V | 1 | RADIAL | جلوگیری از افت rail هنگام روشن‌شدن سگمنت‌ها |
| 27 | C_BYP1..C_BYP15 | خازن بای‌پس هر IC | 100nF | ceramic | 15 | RADIAL | چسبیده به VDD/VSS هر IC منطقی |
| 28 | SW_SET,SW_HOUR,SW_MIN,SW_SECRST,SW_MSTRST | کلید tact | SPST-NO | 6x6mm | 5 | 4-pin | SET / HOUR+ / MIN+ / SEC RESET / MASTER RESET |
| 29 | LED1,LED2 | LED قرمز کولن | Vf≈2.0V | 5mm | 2 | LED | چشمک‌زن ۱ هرتز |
| 30 | J1 | کانکتور تغذیه | 9-12V DC | - | 1 | 2-pin | جک DC یا ترمینال پیچی |

جمع مقاومت‌ها: 42+2+1+6+1+1 = **53**. جمع خازن‌ها: 18p×2 + 100n×16 (۱۵ بای‌پس + C_OUT1) + 0.33µ×1 + 1µ×5 + 10µ×1 + 100µ×2 + 470µ×1 = **28**.
جایگزین‌های سازگار: CD4060B≡HEF4060B≡MC14060B؛ CD4026B≡HEF4026B؛ CD4013B≡HEF4013B؛ CD4081/4071/4093 ≡ HEF4081/4071/4093؛ 7805≡LM7805≡MC7805≡L7805CV (پین‌اوت TO-220 یکسان: 1=IN،2=GND،3=OUT)؛ نمایشگر: هر CC ده‌پین با پین‌اوت جدول (SC52-11EWA تأییدشده؛ SA52-11EWA **آند مشترک است و نباید استفاده شود**).

---

## ۱۲ محاسبات (فرکانس، جریان، زمان‌بندی، حرارت)

**فرکانس:** 32768 = 2^15 Hz. Q14 = ÷2^14 = 2 Hz. ÷2 (FF1) = 1 Hz. اولین لبهٔ بالا دقیقاً t=1.000 s (اثبات سیکل‌دقیق). خطای بلندمدت = خطای کریستال (±20 ppm typ → ≈۱٫۷ s/day).

**بار کریستال:** `CL = C1·C2/(C1+C2) + Cstray = 9p + 3.5p = 12.5p` → کریستال با CL=12.5pF انتخاب شود؛ C1=C2=18pF NP0. R_S=220k محدودکنندهٔ drive؛ R_C=10M بایاس (Fig.13).

**سگمنت‌ها:** CD4026 @5V تضمین می‌کند IOH≥1.6mA در VO≥2.5V. Vf نمایشگر @1.5mA ≈1.8–1.9V (منحنی دیتاشیت؛ typ 2.0V @20mA). `I = (VO−Vf)/R = (2.5−1.9)/470 ≈ 1.3mA` تا `(2.6−1.8)/470 ≈ 1.7mA` → 470Ω ایمن و قابل مشاهده (Iv min 3000µcd@10mA → ≈450µcd@1.5mA). بدترین رقم «8»: 7×1.7 ≈ 12mA per IC ≪ حد پکیج.

**کولن:** `I_LED = (5−2.0−0.2)/1k ≈ 2.8mA` هر LED؛ `IB = (5−0.7)/10k = 0.43mA`؛ β اجباری = 5.6/0.43 ≈ 13 ≪ hFE(min)=100 → اشباع عمیق، VCE≈0.2V.

**بودجهٔ جریان:** typ: 6 رقم × ~4.3 سگمنت × 1.5mA ≈ 39mA + کولن 5.6mA + منطق <1mA ≈ **45mA**. worst («88:88:88» + کولن): 42×1.7+5.6+1 ≈ **78mA**.

**حرارت 7805 (RθJA=65°C/W بدون هیت‌سینک):**
- @12V: `P=(12−0.7−5)×0.078 = 0.49W → ΔT≈32°C → Tj≈57°C` ≪ 150°C ✔
- @9V: `P=(9−0.7−5)×0.078 = 0.26W → ΔT≈17°C` ✔
- مثال خارج از محدوده @24V: `P=(24−0.7−5)×0.078=1.43W → ΔT≈93°C → Tj≈118°C` — نزدیک حد؛ لذا محدودهٔ کاری ۹–۱۲ V اعلام می‌شود.

**زمان‌بندی:** جدول بخش ۷ (پالس‌ها 675/550/800 ns typ در برابر حداقل‌های 220/120 ns). دیبانس: ۸۷ ms رها، POR: ۰٫۸۷ s. تأخیر کری مستقیم: فقط t_CARRY خود IC (typ 250ns) که لبهٔ تمیز داخلی است.

---

## ۱۳) شکل‌موج‌های کلیدی

(نسخهٔ تعاملی در `visuals/waveforms.html`)

```
t(s):        0(reset release) 0.25  0.5   0.75  1.0   1.5   2.0
CLK2HZ(Q14): ____/‾‾‾\____/‾‾‾\____/‾‾‾\____        2Hz
CLK2HZ_INV : ‾‾‾‾\____/‾‾‾\____/‾‾‾\____/‾‾        معکوس
CLK1HZ     : ‾‾‾‾‾‾‾‾‾\_________/‾‾‾‾‾\______   اولین ↑ دقیقاً 1.0s
C_SU       : (پس از 10 لبه) ↑ در گذر 9→0، مربعی 0.1Hz
D6_ST      : ____/‾(675ns typ)\____  در لحظهٔ 59→60 ؛ هم ریست U4 هم کلاک U5
RST_GLOBAL : ‾‾‾‾‾‾‾‾‾‾‾‾‾\_______  (0.87s از روشن‌شدن)
BTN_SET_n  : ‾‾‾\_(فشرده)_/‾‾‾  با بانس آنالوگ؛ BTN_SET = پالس تمیز +87ms دنباله
COLON      : روشن/خاموش با 1Hz (نیم‌دوره 0.5s)
```

---

## ۱۴) آماده‌سازی و ساخت در Proteus

1. پروژهٔ جدید ISIS؛ گزینهٔ simulation را **mixed/digital** بگذارید.
2. قطعات از کتابخانه: `4060`, `4013`, `4026`, `4081`, `4071`, `4093`, `7805`, `2N3904`, `CRYSTAL`, `RES`, `CAP`, `CAP-ELEC`, `BUTTON`, `LED-RED`, `1N4007`, `1N4148`, و نمایشگر `7SEG-COM-CATHODE`.
3. کریستال: frequency=32768، load capacitance=12.5p (اگر مدل پروتئوس پارامتر CL ندارد، C1/C2 خارجی را طبق نتلیست وصل کنید).
4. سیم‌کشی دقیقاً از `netlist/netlist.csv`: هر ردیف = پین→نت؛ از **net label** هم‌نام استفاده کنید تا شلوغ نشود. پایه‌های NC را وصل نکنید؛ ورودی‌های بلااستفاده را به GND (ردیف‌هاعلامت‌گذاری دارند).
5. نمایشگر پروتئوس: پایه‌های A..G مدل را به نت‌های `DSP_x_A..G` (سمت مقاومت) وصل کنید؛ DP بلااستفاده؛ اگر مدل پایهٔ COM دارد به GND (مدل‌های animated پروتئوس معمولاً COM داخلی دارند — پین‌های مدل خود را در Property بررسی کنید).
6. تغذیه: `VSOURCE`/`POWER` ۹–۱۲V به J1؛ زمین‌ها مشترک. برای تست digital می‌توانید VCC را مستقیم ۵V بدهید ولی **برای تست POR/دیبانس حتماً منبع آنالوگ با ramp** استفاده کنید.
7. ابزارها: Logic Analyzer روی CLK1HZ, C_SU, D6_ST, D6_MT, D24, RST_GLOBAL, SET_MODE, CLK_MU, CLK_HU؛ Oscilloscope (آنالوگ) روی POR_N و BTN_SET_n و COLON_K.
8. **هشدار صادقانه:** مدل‌های digital پروتئوس تأخیر ns ندارند → پهنای پالس‌های 675ns در شبیه‌سازی digital به‌صورت ایده‌آل دیده می‌شود؛ اعتبار آن‌ها از محاسبهٔ دیتاشیتی بخش ۷ می‌آید، نه از پروتئوس. برای دیدن پالس واقعی، simulation را mixed با مدل‌های آنالوگ CMOS اجرا کنید یا روی برد با اسکوپ تأیید کنید.
9. سناریوهای تست بخش ۱۵ را اجرا و چک‌لیست را پر کنید. شبیه‌سازی ۲۵ ساعت در حالت digital سریع است (event-driven).

---

## ۱۵) چک‌لیست تست نهایی

| # | سناریو | انتظار | روش مشاهده |
|---|---|---|---|
| 1 | روشن‌شدن | 00:00:00 سپس اولین tick در 1.0s | اسکوپ CLK1HZ + نمایشگر |
| 2 | 00:00:00→00:00:10 | شمارش پیوسته بدون جهش | نمایشگر + analyzer |
| 3 | 00:00:58→00:01:02 | گذر 59→00 دقیقه +۱، ثانیه 00 | analyzer روی D6_ST/CLK_MU |
| 4 | 00:59:58→01:00:02 | D6_MT یک پالس؛ ساعت +۱ | analyzer |
| 5 | 23:59:58→00:00:02 | D24 یک پالس؛ همه صفر | analyzer |
| 6 | SET سپس MIN+ ×3، HOUR+ ×2 | فقط دقیقه/ساعت عوض؛ ثانیه یخ | نمایشگر |
| 7 | فشار همزمان HOUR+ و MIN+ در SET | هر دو یک‌بار افزایش؛ بدون تداخل | analyzer |
| 8 | نگه‌داشتن MIN+ | فقط +۱ | نمایشگر |
| 9 | SEC RESET حین شمارش | ثانیه 00، دقیقه/ساعت دست‌نخورده | نمایشگر |
| 10 | MASTER RESET حین شمارش | 00:00:00 و شروع تمیز | analyzer RST_GLOBAL |
| 11 | power-cycle (خاموش <100ms سپس روشن) | POR کامل دوباره | اسکوپ POR_N |
| 12 | ramp کند تغذیه (100ms) | ریست تا پایداری rail ادامه | اسکوپ |
| 13 | بانس کلید (شبیه‌سازی سوئیچ ایده‌آل + تست واقعی) | یک پالس تمیز | اسکوپ BTN raw vs out |
| 14 | اجرای ۲۵ ساعته | 90061 ثانیه بدون کری گم/اضافه | مقایسه با مرجع (همان verify.js) |
| 15 | کولن | چشمک 1Hz، نیم‌دوره برابر | اسکوپ COLON_K |
| 16 | جریان کل | ≤80mA worst | آمپرمتر سری با منبع |

وضعیت: ردیف‌های ۱–۱۰ و ۱۴ منطقاً در JS تأیید شده؛ **همهٔ ردیف‌ها در Proteus/برد هنوز اجرا نشده‌اند** (بخش ۰).

---

## ۱۶) تحلیل خطاها (cause / effect / detection / fix)

| خطا | اثر | تشخیص | رفع |
|---|---|---|---|
| پین‌اوت اشتباه (مثلاً 7805 یا 2N3904) | عدم عملکرد/آسیب | مقایسه با دیتاشیت سازنده | جدول بخش ۴ فقط از دیتاشیت رسمی |
| قطبیت ریست برعکس | شمارنده ریست نمی‌شود یا همیشه ریست | تست POR | همهٔ ریست‌ها Active HIGHعلامت‌گذاری |
| لبهٔ کلاک اشتباه | شمارش نصف/دوبل | analyzer | CD4013/CD4026 لبهٔ بالا؛ INHIBIT=0 |
| تقسیم ناقص (Q14 بدون ÷2) | 2Hz → ساعت دوبل سریع | فرکانس‌متر | FF1 + اینورتر U15/4 |
| AND/OR جابه‌جا | دیکود همیشه 0/1 | جدول صحت | بخش ۶ |
| MOD-6 اشتباه (ریست در ۵ یا ۷) | دقیقه ۵۰ یا ۷۰ شود | تست مرز | دیکود e·f·g یکتا روی {0..6} |
| MOD-24 اشتباه | ساعت ۲۴ نمایش دهد | تست 23:59:59 | D24=HT2·HU4 |
| کری کوتاه (<220ns) | افزایش گم‌شده | اسکوپ پهنای پالس | محاسبهٔ بخش ۷؛ پشتیبان CD4538 |
| ریست نامعتبر (پالس <120ns) | ریست ناقص | اسکوپ | همان |
| POR نامطمئن | شروع تصادفی | تست ramp/cycle | RC=1s + اشمیت + دیود تخلیه |
| ورودی شناور | رفتار تصادفی/مصرف | بازرسی نتلیست | همهٔ ورودی‌ها بسته؛ unused→GND |
| overload خروجی CMOS | افت VO/گرم‌شدن | محاسبهٔ جریان | 470Ω → ≤1.7mA/سگمنت |
| LED overcurrent | سوختن LED | محاسبه | 1k کولن، 470 سگمنت |
| تداخل SET با کلاک | جهش ثانیه در تنظیم | analyzer | گیت CLK_SEC با nSET_MODE |
| تأخیر گیت‌ها در ریست مشترک | گلیچ/دوبل‌شماری | تحلیل بخش ۷-۳ | جانسون + دیکود مونوتونیک |
| راه‌اندازی کریستال | توقف منبع زمان | اسکوپ XTAL_A | R_C/R_S مطابق Fig13؛ CL صحیح |
| افت rail هنگام روشن‌شدن سگمنت‌ها | ریست کاذب | اسکوپ VCC | C_BULK 470µ + بای‌پس per-IC |
| **CD4518+CD4511 (روش ردشده)** | گلیچ دیکود ناهمگام روی گذر 7→8 (دو بیت همزمان) | تحلیل skew | **رد شد**؛ جایگزین: CD4026 جانسون |
| **دیود-لاجیک برای جمع ریست/کری (ردشده)** | افت ولتاژ + پلاریتهٔ وابسته به جهت دیود؛ سطح HIGH ضعیف برای CMOS | محاسبهٔ VOH | **رد شد**؛ جمع فقط با OR (CD4071) |
| wire-OR کردن خروجی‌ها | contention/آسیب | بازرسی | ممنوع؛ همهٔ جمع‌ها گیت OR |

---

## پیوست: فایل‌های تحویلی

| فایل | محتوا |
|---|---|
| `netlist/netlist.csv` | ۴۸۴ پین→نت (مرجع بازسازی شماتیک/Proteus) |
| `netlist/nets.csv` | فرهنگ ۱۳۷ نت |
| `netlist/bom.csv` | BOM مطابق شماتیک |
| `netlist/proteus_wiring.md` | برگهٔ سیم‌کشی گروه‌بندی‌شده بر حسب نت (۱۳۶ نت) |
| `docs/proteus_guide_fa.md` | راهنمای گام‌به‌گام Proteus + چک‌لیست تست با وضعیت «در انتظار» |
| `netlist/gen_netlist.py` | منبع واحد تولید + sanity checks |
| `sim/verify.js` | تأیید منطق ۲۵ ساعته + مرزها + set/reset |
| `sim/divider_check.js` | اثبات فاز/فرکانس پایهٔ زمان |
| `visuals/schematic.html` | شماتیک بلوکی تعاملی با پین‌ها |
| `visuals/waveforms.html` | شکل‌موج‌های کلیدی |
| `research/` | دیتاشیت‌های رسمی + رندر صفحات تأیید |

منابع دیتاشیت: TI CD4060B (SCHS049C)، TI CD4026B، TI CD4013B، TI CD4081B/CD4071B/CD4093B، ON Semi MC7800 (mc7800-d)، Kingbright SC52-11EWA (DSAC0696).

</div>