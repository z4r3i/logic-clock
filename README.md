<div dir="rtl">

# ساعت دیجیتال تمام‌سخت‌افزاری ۲۴ ساعته

ساعت دیجیتال **کاملاً سخت‌افزاری** — بدون هیچ میکروکنترلر، برنامه یا FPGA.
پایهٔ زمان: کریستال ۳۲٫۷۶۸ kHz → CD4060B (تقسیم ۲¹⁴) → CD4013B (تقسیم بر ۲) → **۱ Hz دقیق**.
شمارش و نمایش: شش عدد CD4026B به صورت MOD-60 / MOD-60 / MOD-24 روی شش نمایشگر ۷ سگمنت کاتد مشترک، با کولن چشمک‌زن ۱ Hz.
تغذیه: ورودی ۹–۱۲ V DC → رگولاتور 7805 → ۵ V.

**۱۳۷ نت · ۴۸۴ پین · ۱۱۵ قطعه · ۱۶ IC** — همهٔ اتصالات با شمارهٔ پین دقیق در [نت‌لیست](netlist/netlist.csv) و [برگهٔ سیم‌کشی](netlist/proteus_wiring.md).

---

## مشاهدهٔ سریع

| صفحه | توضیح |
|---|---|
| [نمایهٔ پروژه](https://z4r3i.github.io/logic-clock/index.html) | صفحهٔ اصلی برای GitHub Pages |
| [نقشهٔ کامل مدار](https://z4r3i.github.io/logic-clock/visuals/circuit_schematic.html) | شماتیک تعاملی تمام قطعات؛ کلیک روی هر نت = ردیابی همهٔ اتصالات آن |
| [شبیه‌ساز ساعت](https://z4r3i.github.io/logic-clock/visuals/clock_simulator.html) | شبیه‌سازی نت‌محور با همان نت‌لیست واقعی؛ دکمه‌ها، ریست و تنظیم ساعت |
| [شماتیک بلوکی + جدول پین‌ها](https://z4r3i.github.io/logic-clock/visuals/schematic.html) | نمای بلوکی ۱۱ بلوک با جدول پین هر IC |
| [شکل‌موج‌ها](https://z4r3i.github.io/logic-clock/visuals/waveforms.html) | شکل‌موج پایهٔ زمان، کری/ریست و دیبانس |

همهٔ HTMLها **مستقل و بدون وابستگی خارجی** هستند؛ کافی است فایل را در مرورگر باز کنید (یا از طریق GitHub Pages ببینید).

## داکیومنت‌ها

- [راهنمای ساخت](docs/proteus_guide.md) — چک‌لیست راه‌اندازی (Proteus اختیاری است؛ برای برد واقعی معتبر است)
- [برگهٔ سیم‌کشی گروه‌بندی‌شده](netlist/proteus_wiring.md) — هر نت و همهٔ پین‌های آن
- [نت‌لیست کامل](netlist/netlist.csv) · [شرح نت‌ها](netlist/nets.csv) · [لیست قطعات (BOM)](netlist/bom.csv)

## ساختار مخزن

```
digital-clock/
├── index.html                  ← صفحهٔ اصلی GitHub Pages
├── docs/
│   ├── design_fa.md            ← سند طراحی کامل (محاسبات + تأیید)
│   └── proteus_guide_fa.md     ← راهنمای ساخت و چک‌لیست تست
├── netlist/
│   ├── netlist.csv             ← مرجع یگانهٔ سیم‌کشی (۴۸۴ پین)
│   ├── nets.csv                ← شرح ۱۳۷ نت
│   ├── bom.csv                 ← لیست قطعات
│   ├── proteus_wiring.md       ← برگهٔ سیم‌کشی گروه‌بندی‌شده
│   └── gen_netlist.py          ← مولد نت‌لیست/BOM
├── sim/
│   ├── clock_engine.js         ← موتور شبیه‌سازی نت‌محور
│   ├── verify.js               ← تأیید منطق ۲۵ ساعت + مرزها
│   ├── divider_check.js        ← تأیید سیکل‌دقیق پایهٔ زمان
│   └── engine_test.js          ← تست موتور نت‌محور
└── visuals/
    ├── circuit_schematic.html  ← نقشهٔ کامل مدار (تعاملی)
    ├── clock_simulator.html    ← شبیه‌ساز ساعت
    ├── schematic.html          ← شماتیک بلوکی + پین‌ها
    ├── waveforms.html          ← شکل‌موج‌ها
    ├── gen_full_schematic.py   ← مولد نقشهٔ کامل از netlist.csv
    ├── gen_visuals.py          ← مولد شماتیک بلوکی
    ├── build_sim.py            ← مولد شبیه‌ساز (sim_ui.html + موتور)
    └── sim_ui.html             ← قالب رابط شبیه‌ساز
```


## وضعیت تأیید — صادقانه

| بخش | روش | وضعیت |
|---|---|---|
| منطق شمارش، کری/ریست، مرزهای 60/60/24، تنظیم و ریست | شبیه‌سازی تابعی JS روی ۹۰۰۶۱ ثانیه (۲۵ ساعت) | ✅ تأیید شده (`sim/verify.js`) |
| فاز و فرکانس پایهٔ زمان (اولین لبه دقیقاً t=1.000s) | شبیه‌سازی سیکل‌دقیق ۱۶۳۸۴۰ سیکل اسیلاتور | ✅ تأیید شده (`sim/divider_check.js`) |
| موتور نت‌محور (همان نت‌لیست واقعی) | تست تطابق با منطق اثبات‌شده | ✅ تأیید شده (`sim/engine_test.js`) |
| پین‌اوت‌ها و عرض پالس‌ها | دیتاشیت رسمی + محاسبهٔ typ/max | ✅ تأیید/محاسبه شده |
| راه‌اندازی کریستال، دیبانس آنالوگ، جریان LED، رفتار تغذیه | محاسبهٔ مداری | ⚠️ نیازمند تأیید روی برد واقعی |
| شبیه‌سازی آنالوگ Proteus / تست سخت‌افزار | — | ❌ انجام نشده — این مخزن ادعای «تأیید نهایی سخت‌افزاری» ندارد |

## اجرای تست‌ها

نیازمندی: فقط [Node.js](https://nodejs.org) (بدون هیچ پکیج خارجی).

```bash
node sim/verify.js          # منطق کامل ۲۵ ساعت + مرزها + عرض پالس
node sim/divider_check.js   # فاز/فرکانس پایهٔ زمان (سیکل‌دقیق)
node sim/engine_test.js     # موتور نت‌محور
```

هر سه باید با `PASSED` تمام شوند.

## بازتولید خروجی‌ها

نیازمندی: Python 3 (بدون پکیج خارجی).

```bash
python netlist/gen_netlist.py          # netlist.csv / nets.csv / bom.csv
python visuals/gen_visuals.py          # schematic.html
python visuals/gen_full_schematic.py   # circuit_schematic.html (از netlist.csv)
python visuals/build_sim.py            # clock_simulator.html
```

## مشخصات کلیدی

- **دقت زمان:** کریستال ۳۲٫۷۶۸ kHz؛ خطای تقسیم صفر (تقسیم دیجیتال خالص). خطای نهایی = خطای کریستال (معمولاً ±۲۰ ppm ≈ ۱٫۷ ثانیه در روز).
- **ریست خودکار روشن‌شدن (POR):** ≈۰٫۸۷ ثانیه → نمایش `00:00:00`.
- **۵ کلید دیبانس‌شده** (RC + اشمیت تریگر CD4093): SET، HOUR+، MIN+، SEC RESET، MASTER RESET.
- **نمایش:** SC52-11EWA کاتد مشترک + ۴۲ مقاومت ۴۷۰ Ω (≈۴٫۳ mA per segment)؛ کولن با ترانزیستور 2N3904 و دو LED.
- **مصرف تخمینی:** < ۵۰ mA در ۵ V (بسته به روشنایی سگمنت‌ها).

</div>
