<div dir="rtl">

# ساعت دیجیتال تمام‌سخت‌افزاری ۲۴ ساعته

ساعت دیجیتال **کاملاً سخت‌افزاری** — بدون هیچ میکروکنترلر، برنامه یا FPGA.
پایهٔ زمان: کریستال ۳۲٫۷۶۸ kHz → CD4060B (تقسیم ۲¹⁴) → CD4013B (تقسیم بر ۲) → **۱ Hz دقیق**.
شمارش و نمایش: شش عدد CD4026B به صورت MOD-60 / MOD-60 / MOD-24 روی شش نمایشگر ۷ سگمنت کاتد مشترک، با کولن چشمک‌زن ۱ Hz.
تغذیه: ورودی ۹–۱۲ V DC → رگولاتور 7805 → ۵ V.

**۱۳۷ نت (۱۳۶ قابل سیم‌کشی + NC) · ۴۸۴ پین · ۱۱۵ قطعه · ۱۶ IC** — همهٔ اتصالات با شمارهٔ پین دقیق در [نت‌لیست](netlist/netlist.csv) و [برگهٔ سیم‌کشی](netlist/proteus_wiring.md).

---

## مشاهدهٔ سریع

| صفحه | توضیح |
|---|---|
| [نمایهٔ پروژه](https://z4r3i.github.io/logic-clock/index.html) | صفحهٔ اصلی برای GitHub Pages |
| [آزمایشگاه ترکیبی نقشه و شبیه‌ساز](https://z4r3i.github.io/logic-clock/visuals/circuit_lab.html) | تمام قطعات و پایه‌های زنده، ورودی/خروجی، ریزگام انتشار، مرور رخداد، شکل‌موج و سناریوهای آموزشی؛ مدل منطقیِ **نت‌محور** (از netlist)، نه SPICE |
| [راهنمای ساخت و سیم‌کشی مبتدی](https://z4r3i.github.io/logic-clock/visuals/build_guide_fa.html) | جای‌گذاری بلوکی + سیم‌کشی نت‌به‌نت + کد رنگ مقاومت و کد خازن؛ [PDF قابل‌پرینت](visuals/build_guide_fa.pdf) |
| [نقشه فیزیکی ساخت (تخته + سیم لاکی)](https://z4r3i.github.io/logic-clock/visuals/physical_wiring.html) | چیدمان واقعی ۱۱۵ قطعه و ۲۵۳ سیم نقطه‌به‌نقطه **بدون هیچ هم‌پوشانی**؛ ۳۹۱ مرحله ساخت با طول برش و آزمایش هر بخش؛ نمای آینه‌ای سمتِ لحیم؛ [PDF دوازده‌صفحه‌ای فاز‌به‌فاز با جدول سیم‌ها](visuals/physical_wiring.pdf) |
| [نقشهٔ کامل مدار](https://z4r3i.github.io/logic-clock/visuals/circuit_schematic.html) | شماتیک تعاملی تمام قطعات؛ کلیک روی هر نت = ردیابی همهٔ اتصالات آن |
| [شبیه‌ساز ساعت](https://z4r3i.github.io/logic-clock/visuals/clock_simulator.html) | مدل تابعی ICها با همان نام/شمارهٔ پایه‌های نت‌لیست؛ دکمه‌ها، ریست و تنظیم ساعت |
| [شماتیک بلوکی + جدول پین‌ها](https://z4r3i.github.io/logic-clock/visuals/schematic.html) | نمای بلوکی ۱۱ بلوک با جدول پین هر IC |
| [شکل‌موج‌ها](https://z4r3i.github.io/logic-clock/visuals/waveforms.html) | شکل‌موج پایهٔ زمان، کری/ریست و دیبانس |

همهٔ HTMLها **مستقل و بدون وابستگی خارجی** هستند؛ کافی است فایل را در مرورگر باز کنید (یا از طریق GitHub Pages ببینید).

## گزینهٔ جایگزین: نسخهٔ تمام‌ترانزیستوری (بدون هیچ IC)

پوشهٔ [transistor-clock/](transistor-clock/) یک نسخهٔ **کاملاً گسسته** از همین ساعت است: فقط ترانزیستور 2N3904، دیود 1N4148، مقاومت/خازن — بدون هیچ IC، میکروکنترلر یا برنامه. همان معماری (کریستال ۳۲٫۷۶۸ kHz → تقسیم بر ۳۲۷۶۸ → ۱ Hz → شش رقم MOD-60/60/24) با سلول‌های TFF/DTL/دیکودر دیودی.

| صفحه | توضیح |
|---|---|
| [بررسی سختی و ارزش (داشبورد تعاملی)](transistor-clock/visuals/assessment.html) | مقایسهٔ CMOS با گسسته، شمارش قطعات هر بلوک، مدار سلول‌ها، حکم ارزش |
| [سند طراحی کامل](transistor-clock/docs/design_fa.md) | محاسبات بایاس/استیرینگ/سرعت، معادلات سگمنت، رد روش‌های نامطمئن |
| [مقایسهٔ CMOS و ترانزیستوری](transistor-clock/docs/ring_vs_cmos_fa.md) | مقایسهٔ صادقانهٔ معماری حلقوی مرجع با CMOS و نسخهٔ گسستهٔ باینری |
| [نت‌لیست ۳۰۷۹ پین](transistor-clock/netlist/netlist.csv) · [BOM](transistor-clock/netlist/bom.csv) | مرجع سیم‌کشی نسخهٔ گسسته |
| [README نسخهٔ ترانزیستوری](transistor-clock/README.md) | اعداد کلیدی، اجرای تست‌ها، مسیر کم‌ریسک |

**حکم (صادقانه):** ۱۴۳۰ قطعه / ۱۶۹ ترانزیستور / ۳۰۷۹ پین در برابر ۱۱۵ قطعه / ۴۸۴ پین CMOS — یعنی ≈۱۲٫۴× قطعه و ≈۶٫۴× پایه، ≈۱۰× زمان ساخت (۱۰۰–۲۰۰ ساعت)، ≈۴× هزینه و ≈۲× مصرف، با **همان دقت**. به‌عنوان ساعت عملی **ارزش ندارد**؛ به‌عنوان پروژهٔ آموزشی **ارزش دارد**. گزینهٔ پیشنهادی برای ساخت، همین نسخهٔ CMOS است.

> وضعیت تأیید نسخهٔ ترانزیستوری: منطق (۲۵ ساعت + مرزها + دیکودرها) با `transistor-clock/sim/verify.js` تأیید شده؛ رفتار آنالوگ (اسیلاتور پیرس، سلول TFF، درایورها) **نیازمند SPICE + بنچ‌تست** است و «تأییدشدهٔ سخت‌افزاری» اعلام نمی‌شود.

## داکیومنت‌ها

- [راهنمای ساخت](docs/design_fa.md) — چک‌لیست راه‌اندازی (Proteus اختیاری است؛ برای برد واقعی معتبر است)
- [چک‌لیست خرید قطعات](docs/shopping_checklist_fa.html) — [PDF](docs/shopping_checklist_fa.pdf)
- [برگهٔ سیم‌کشی گروه‌بندی‌شده](netlist/proteus_wiring.md) — هر نت و همهٔ پین‌های آن
- [نت‌لیست کامل](netlist/netlist.csv) · [شرح نت‌ها](netlist/nets.csv) · [لیست قطعات (BOM)](netlist/bom.csv)

## ساختار مخزن

```
digital-clock/
├── index.html                  ← صفحهٔ اصلی GitHub Pages
├── docs/
│   ├── design_fa.md            ← سند طراحی کامل (محاسبات + تأیید)
│   ├── proteus_guide_fa.md     ← راهنمای ساخت و چک‌لیست تست
│   └── shopping_checklist_fa.html/.pdf ← چک‌لیست خرید
├── netlist/
│   ├── netlist.csv             ← مرجع یگانهٔ سیم‌کشی (۴۸۴ پین)
│   ├── nets.csv                ← شرح ۱۳۷ نت
│   ├── bom.csv                 ← لیست قطعات
│   ├── proteus_wiring.md       ← برگهٔ سیم‌کشی گروه‌بندی‌شده
│   └── gen_netlist.py          ← مولد نت‌لیست/BOM
├── sim/
│   ├── clock_engine.js         ← موتور تابعی هم‌ارز نت‌لیست
│   ├── circuit_engine.js       ← مدل منطقی نت‌محور (از COMP نت‌لیست)
│   ├── verify.js               ← تأیید منطق ۲۵ ساعت + مرزها
│   ├── divider_check.js        ← تأیید سیکل‌دقیق پایهٔ زمان
│   ├── engine_test.js          ← تست POR/۲۵ ساعت/۶۰fps موتور تابعی
│   └── circuit_engine_test.js  ← تست مدل نت‌محور + ۴۸۴ پین
├── visuals/
│   ├── circuit_schematic.html  ← نقشهٔ کامل مدار (تعاملی)
│   ├── circuit_lab.html        ← نقشه + مدل منطقی نت‌محور
│   ├── clock_simulator.html    ← شبیه‌ساز ساعت (تابعی)
│   ├── schematic.html          ← شماتیک بلوکی + پین‌ها
│   ├── waveforms.html          ← شکل‌موج‌ها
│   ├── build_guide_fa.html     ← راهنمای ساخت مبتدی
│   ├── physical_wiring.html    ← نقشه فیزیکی ساخت (تخته + سیم لاکی)
│   ├── physical_wiring_ui.html ← قالب رابط + pw_draw.js/pw_app.js (رندر و مرحله‌به‌مرحله)
│   ├── gen_visuals.py          ← مولد شماتیک بلوکی
│   ├── gen_full_schematic.py   ← مولد نقشهٔ کامل از netlist.csv
│   ├── gen_build_guide.py      ← مولد راهنمای ساخت
│   ├── gen_physical_wiring.py  ← مولد نقشهٔ فیزیکی
│   ├── gen_physical_print.py   ← مولد نسخهٔ چاپی فاز‌به‌فاز
│   ├── board_layout.py         ← چیدمان برد
│   ├── board_model.py          ← مدل سیم‌کشی/گام‌ها
│   ├── board_router.py         ← مسیریابی بدون هم‌پوشانی
│   ├── build_sim.py            ← مولد شبیه‌ساز (sim_ui.html + موتور)
│   └── sim_ui.html             ← قالب رابط شبیه‌ساز
└── transistor-clock/           ← گزینهٔ جایگزین: نسخهٔ تمام‌ترانزیستوری
    ├── docs/design_fa.md       ← سند طراحی گسسته + محاسبات + حکم ارزش
    ├── docs/ring_vs_cmos_fa.md ← مقایسهٔ حلقوی/CMOS/باینری
    ├── netlist/                ← netlist.csv / nets.csv / bom.csv + مولد
    ├── sim/verify.js           ← تأیید منطق ۲۵ ساعت نسخهٔ گسسته
    └── visuals/assessment.html ← داشبورد تعاملی سختی/ارزش
```


## وضعیت تأیید — صادقانه

| بخش | روش | وضعیت |
|---|---|---|
| منطق شمارش، کری/ریست، مرزهای 60/60/24، تنظیم و ریست | شبیه‌سازی تابعی JS روی ۹۰۰۶۱ ثانیه (۲۵ ساعت) | ✅ تأیید شده (`sim/verify.js`) |
| فاز و فرکانس پایهٔ زمان (اولین لبه ۱٫۰۰۰s پس از رهاسازی POR) | شبیه‌سازی سیکل‌دقیق ۱۶۳۸۴۰ سیکل اسیلاتور | ✅ تأیید شده (`sim/divider_check.js`) |
| موتور تابعی با نام/پایه‌های نت‌لیست | POR، اولین تیک ۱٫۸۷s، ۲۵ ساعت، مرزها و ۶۰fps | ✅ تأیید شده (`sim/engine_test.js`) |
| مدل منطقی نت‌محور (circuit_lab) | گیت‌ها/فلیپ‌فلاپ‌ها از COMP نت‌لیست + ۴۸۴ پین | ✅ ۱۹ تست (`sim/circuit_engine_test.js`) |
| پین‌اوت‌ها و عرض پالس‌ها | دیتاشیت رسمی + محاسبهٔ typ/max | ✅ تأیید/محاسبه شده |
| راه‌اندازی کریستال، دیبانس آنالوگ، جریان LED، رفتار تغذیه | محاسبهٔ مداری | ⚠️ نیازمند تأیید روی برد واقعی |
| شبیه‌سازی آنالوگ Proteus / تست سخت‌افزار | — | ❌ انجام نشده — این مخزن ادعای «تأیید نهایی سخت‌افزاری» ندارد |

## اجرای تست‌ها

نیازمندی: فقط [Node.js](https://nodejs.org) (بدون هیچ پکیج خارجی).

```bash
node sim/verify.js          # منطق کامل ۲۵ ساعت + مرزها + عرض پالس
node sim/divider_check.js   # فاز/فرکانس پایهٔ زمان (سیکل‌دقیق)
node sim/engine_test.js     # موتور تابعی هم‌ارز نت‌لیست
```

خروجی‌های مورد انتظار:

- `verify.js` → `ALL VERIFICATION PASSED`
- `divider_check.js` → `DIVIDER PHASE OK`
- `engine_test.js` → `ALL ENGINE TESTS PASSED`

مدل آموزشی مستقلِ صفحهٔ ترکیبی، پالس‌های گذرای دیکود/ریست و گیت‌های واقعی نت‌لیست را نیز ثبت می‌کند:

```bash
node sim/circuit_engine_test.js
```

«ریزگام انتشار» ترتیب منطقی مدل است، نه تأخیر اندازه‌گیری‌شدهٔ قطعه. مقادیر آنالوگ با `A` و پایه‌های بدون اتصال با `NC` مشخص می‌شوند؛ رفع POR در ۰٫۸۷ ثانیه و کلیدهای بدون جهش از فرض‌های این مدل‌اند. تست این مدل با پیام `19 tests passed ... 484 physical pins checked` تمام می‌شود.

## بازتولید خروجی‌ها

نیازمندی: Python 3 (بدون پکیج خارجی).

```bash
python netlist/gen_netlist.py              # netlist.csv / nets.csv / bom.csv
python visuals/gen_visuals.py              # schematic.html
python visuals/gen_full_schematic.py       # circuit_schematic.html (از netlist.csv)
python visuals/gen_full_schematic.py --lab # circuit_lab.html (نقشه + مدل نت‌محور)
python visuals/gen_build_guide.py          # build_guide_fa.html
python visuals/gen_physical_wiring.py      # physical_wiring.html (+ مدل JSON)
python visuals/gen_physical_print.py       # physical_wiring_print.html (از مدل JSON)
python visuals/build_sim.py                # clock_simulator.html
```

PDFهای موجود از همین HTMLها با **Print → Save as PDF** مرورگر ساخته می‌شوند (A4؛ نقشهٔ فیزیکی A4 landscape). بعد از هر تغییر، HTML مربوط را دوباره تولید و سپس PDF را از همان فایل چاپ کن.

## مشخصات کلیدی

- **دقت زمان:** کریستال ۳۲٫۷۶۸ kHz؛ خطای تقسیم صفر (تقسیم دیجیتال خالص). خطای نهایی = خطای کریستال (معمولاً ±۲۰ ppm ≈ ۱٫۷ ثانیه در روز).
- **ریست خودکار روشن‌شدن (POR):** ≈۰٫۸۷ ثانیه → نمایش `00:00:00`؛ اولین تیک معتبر در ≈۱٫۸۷ ثانیه.
- **۵ کلید دیبانس‌شده** (RC + اشمیت تریگر CD4093): SET، HOUR+، MIN+، SEC RESET، MASTER RESET.
- **U1:** CD4060B در پکیج **DIP-16** (روی سوکت)؛ هم‌راستا با بقیهٔ ICهای دیپ.
- **نمایش:** SC52-11EWA کاتد مشترک + ۴۲ مقاومت ۴۷۰ Ω (≈۱٫۵ mA per segment؛ typ ≈۴۵ mA، worst ≈۷۸ mA)؛ کولن با ترانزیستور 2N3904 و دو LED.
- **مصرف تخمینی:** typ ≈۴۵ mA و worst ≈۷۸ mA در ۵ V (بسته به تعداد سگمنت‌های روشن).

</div>
