# -*- coding: utf-8 -*-
"""Beginner build guide: block placement map + complete net-by-net wiring tables
+ resistor color codes + capacitor markings, generated from netlist.csv.
Emits build_guide_fa.html (standalone, printable)."""
import csv, os, io, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(OUT)

comps = {}
with open(os.path.join(BASE, 'netlist', 'netlist.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        c = comps.setdefault(r['Ref'], {'model': r['Model'], 'value': r['Value'], 'pkg': r['Package'], 'pins': {}})
        c['pins'][r['Pin']] = (r['PinName'], r['Net'], r['Notes'])
netdesc = {}
with open(os.path.join(BASE, 'netlist', 'nets.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        netdesc[r['Net']] = r['Description']

# ---- resistor 4-band color code ----
DIGCOL = ['مشکی', 'قهوه‌ای', 'قرمز', 'نارنجی', 'زرد', 'سبز', 'آبی', 'بنفش', 'خاکستری', 'سفید']
DIGHEX = ['#111111', '#7b4a2d', '#d3312e', '#f07818', '#f2c200', '#2e9e44', '#2f6fd0', '#8b4fc9', '#8a8f98', '#f5f5f5']
MULTHEX = DIGHEX + ['#c9a227', '#c0c0c0']  # 10^-1 gold, 10^-2 silver
def ohms(v):
    v = v.strip()
    if v.endswith('R'): return float(v[:-1])
    if v.endswith('k'): return float(v[:-1]) * 1e3
    if v.endswith('M'): return float(v[:-1]) * 1e6
    return float(v)
def bands(v):
    n = int(round(ohms(v)))
    s = str(n)
    core = s.rstrip('0')
    if len(core) < 2: core = (core + '0')[:2]
    core = core[:2]
    m = len(s) - len(core)
    d1, d2 = int(core[0]), int(core[1])
    return [(DIGHEX[d1], DIGCOL[d1]), (DIGHEX[d2], DIGCOL[d2]),
            (MULTHEX[m], '×۱۰^' + str(m)), ('#c9a227', '±۵٪ طلایی')]
RES_VALUES = ['470R', '1k', '10k', '100k', '220k', '10M']

CAP_INFO = {
    '18pF': ('180 / 18', 'سرامیک NP0/C0G', False, '۵۰V'),
    '100nF': ('104', 'سرامیک X7R', False, '۵۰V'),
    '1uF': ('105', 'سرامیک X7R (فیلم هم مجاز)', False, '≥۱۶V'),
    '0.33uF': ('334', 'فیلم پلی‌استر / سرامیک', False, '≥۵۰V'),
    '10uF': ('10µF', 'الکترولیت', True, '۱۶V'),
    '100uF': ('100µF', 'الکترولیت', True, '۲۵V ورودی / ۱۶V خروجی'),
    '470uF': ('470µF', 'الکترولیت', True, '۱۶V'),
}
CAP_VOLT_REF = {'C_POR': '۱۶V', 'C_IN2': '۲۵V', 'C_OUT2': '۱۶V', 'C_BULK': '۱۶V'}

# ---- placement zones (assembly order) ----
def digit_refs(dig, uref, ds):
    return [uref] + ['R_%s%s' % (dig, s) for s in 'ABCDEFG'] + [ds]
ZONES = [
    ('POWER', '۱) تغذیه و رگولاتور', ['J1', 'D1', 'U16', 'C_IN1', 'C_IN2', 'C_OUT1', 'C_OUT2', 'C_BULK']),
    ('POR', '۲) ریست روشن‌شدن', ['R_POR', 'C_POR', 'D2']),
    ('TIMEBASE', '۳) پایه زمان (4060 DIP-16 + کریستال + 4013)', ['U1', 'Y1', 'C1', 'C2', 'R_C', 'R_S', 'U2']),
    ('SCHMITT', '۴) اشمیت تریگرها', ['U14', 'U15']),
    ('GATES', '۵) گیت‌های دیکود و مسیریابی', ['U9', 'U10', 'U11', 'U12', 'U13']),
    ('BUTTONS', '۶) کلیدها + دیبانس', [x for n in ['SET', 'HOUR', 'MIN', 'SECRST', 'MSTRST']
                                       for x in ('SW_' + n, 'R_PU_' + n, 'C_BTN_' + n)]),
    ('DIG_HT', '۷) دهگان ساعت', digit_refs('HT', 'U8', 'DS1')),
    ('DIG_HU', '۸) یکان ساعت', digit_refs('HU', 'U7', 'DS2')),
    ('DIG_MT', '۹) دهگان دقیقه', digit_refs('MT', 'U6', 'DS3')),
    ('DIG_MU', '۱۰) یکان دقیقه', digit_refs('MU', 'U5', 'DS4')),
    ('DIG_ST', '۱۱) دهگان ثانیه', digit_refs('ST', 'U4', 'DS5')),
    ('DIG_SU', '۱۲) یکان ثانیه', digit_refs('SU', 'U3', 'DS6')),
    ('COLON', '۱۳) کولن چشمک‌زن', ['R_CB', 'Q1', 'R_CL1', 'R_CL2', 'LED1', 'LED2']),
    ('BYPASS', '۱۴) بای‌پس‌ها (چسبیده به هر IC)', ['C_BYP%d' % i for i in range(1, 16)]),
]
placed = set()
for _, _, refs in ZONES: placed.update(refs)
assert placed == set(comps), 'placement missing/extra: %s' % (placed ^ set(comps))

# ---- wiring groups ----
def wire_color(n):
    if n == 'VCC': return '#e05252'
    if n == 'GND': return '#9aa4b2'
    if n in ('VIN', 'VIN2'): return '#f0883e'
    if n.startswith('XTAL_') or n == 'OSC_FB': return '#b18cff'
    if n.startswith('CLK') or n.startswith('FF') or n in ('HOUR_GATE', 'MIN_GATE'): return '#58a6ff'
    if n.startswith('BTN') or n in ('SET_MODE', 'nSET_MODE'): return '#f778ba'
    if n.startswith('RST') or n.startswith('POR') or n in ('D24', 'D6_ST', 'D6_MT', 'HT2', 'HU4', 'ST_EF', 'MT_EF', 'HT_AD', 'HU_CF'): return '#e3b341'
    if n.startswith('C_'): return '#7ee787'
    if n.startswith('SEG_') or n.startswith('DSP_'): return '#39c5cf'
    if n.startswith('COLON'): return '#d29922'
    return '#8b949e'
def group_of(n):
    if n in ('VCC', 'GND', 'NC'): return None
    if n in ('VIN', 'VIN2'): return 'POWER'
    if n in ('POR_N', 'POR_RST'): return 'POR'
    if n in ('XTAL_A', 'XTAL_B', 'OSC_FB', 'CLK2HZ', 'CLK2HZ_INV', 'CLK1HZ', 'FF1_D', 'FF2_D', 'SET_MODE', 'nSET_MODE'): return 'TIMEBASE'
    if n.startswith('BTN_'): return 'BUTTONS'
    if n.startswith('SEG_') or n.startswith('DSP_'): return 'DIG_' + n.split('_')[1]
    if n.startswith('COLON'): return 'COLON'
    return 'GATES'
netpins = {}
for ref, c in comps.items():
    for p, (name, net, note) in c['pins'].items():
        if net in ('VCC', 'GND', 'NC'): continue
        netpins.setdefault(net, []).append((ref, int(p), name))
for v in netpins.values(): v.sort(key=lambda t: (t[0], t[1]))
GROUP_ORDER = ['POWER', 'POR', 'TIMEBASE', 'BUTTONS', 'GATES', 'DIG_HT', 'DIG_HU', 'DIG_MT', 'DIG_MU', 'DIG_ST', 'DIG_SU', 'COLON']
GROUP_TITLE = {z[0]: z[1] for z in ZONES}
groups = {g: [] for g in GROUP_ORDER}
for net, pins in netpins.items():
    g = group_of(net)
    if g: groups[g].append(net)
for g in groups: groups[g].sort()

# ---- placement (HTML zones, paginate cleanly in print) ----
def label(ref):
    c = comps[ref]
    v = c['value'] if c['value'] not in ('-', '') else c['model']
    return ref + ' · ' + v
place = []
for zid, title, refs in ZONES:
    chips = ''.join('<span class="chip">%s</span>' % label(r) for r in refs)
    place.append('<div class="zone"><h4>%s</h4><div class="chips">%s</div></div>' % (title, chips))
PLACE = ''.join(place)

# ---- resistor cards ----
res_html = []
for v in RES_VALUES:
    b = bands(v)
    stripes = ''.join('<rect x="%d" y="6" width="10" height="38" fill="%s"/>' % (34 + i * 22, col) for i, (col, _) in enumerate(b))
    names = ' ، '.join(nm for _, nm in b)
    cnt = sum(1 for c in comps.values() if c['model'] == 'resistor' and c['value'] == v)
    res_html.append('<div class="rcard"><svg viewBox="0 0 150 50" class="rsvg"><line x1="0" y1="25" x2="150" y2="25" stroke="#8a8f98" stroke-width="3"/><rect x="24" y="6" width="102" height="38" rx="8" fill="#d9c9a3"/>%s</svg><div><b class="mono">%s</b> ×%d<br><span class="muted">%s</span></div></div>' % (stripes, v, cnt, names))

# ---- capacitor table ----
cap_rows = []
seen = set()
for ref, c in comps.items():
    if not c['model'].startswith('cap'): continue
    v = c['value']
    if v in seen: continue
    seen.add(v)
    code, typ, pol, volt = CAP_INFO[v]
    if ref in CAP_VOLT_REF: volt = CAP_VOLT_REF[ref]
    cnt = sum(1 for cc in comps.values() if cc['model'].startswith('cap') and cc['value'] == v)
    cap_rows.append('<tr><td class="mono">%s</td><td class="mono">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td></tr>' % (v, code, typ, 'قطبی (+/−)' if pol else 'غیرقطبی', volt, cnt))

# ---- wiring tables ----
wire_html = []
for g in GROUP_ORDER:
    if not groups[g]: continue
    rows = []
    for net in groups[g]:
        pins = netpins[net]
        plist = ' , '.join('%s.%d (%s)' % (r, p, nm) for r, p, nm in pins)
        rows.append('<tr><td><span class="wchip" style="--wc:%s">%s</span></td><td class="desc">%s</td><td class="pins">%s</td><td>%d</td></tr>' % (wire_color(net), net, netdesc.get(net, ''), plist, len(pins)))
    wire_html.append('<h3>%s</h3><table class="wt"><tr><th>نت / رنگ سیم</th><th>توضیح</th><th>همه پایه‌هایی که باید به هم وصل شوند</th><th>تعداد</th></tr>%s</table>' % (GROUP_TITLE[g], ''.join(rows)))

rails_vcc = sum(1 for c in comps.values() for p in c['pins'].values() if p[1] == 'VCC')
rails_gnd = sum(1 for c in comps.values() for p in c['pins'].values() if p[1] == 'GND')

HTML = '''<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">
<title>راهنمای ساخت و سیم‌کشی مبتدی — ساعت CMOS</title>
<style>
@page{size:A4;margin:12mm}
:root{--bg:#0d1117;--panel:#161b22;--line:#303b49;--txt:#e6edf3;--mut:#9caabb;--acc:#8bcaff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:13px/1.8 Tahoma,'Segoe UI',sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:20px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;color:var(--acc);margin:26px 0 8px;border-bottom:1px solid var(--line);padding-bottom:5px}
h3{font-size:13px;color:var(--acc);margin:16px 0 6px}.muted{color:var(--mut)}.mono{font-family:Consolas,monospace;direction:ltr;unicode-bidi:embed;display:inline-block}
.sub{color:var(--mut);font-size:12px}
table{border-collapse:collapse;width:100%;font-size:11.5px;margin:6px 0}
th,td{border:1px solid var(--line);padding:5px 7px;text-align:right;vertical-align:top}
th{background:var(--panel);color:var(--mut);font-weight:normal}
.wchip{display:inline-block;padding:1px 8px;border-radius:10px;border:1px solid var(--wc);color:var(--wc);font:11px Consolas,monospace;direction:ltr}
.pins,.desc{direction:ltr;text-align:left;font-family:Consolas,monospace;font-size:10.5px}
.desc{color:var(--mut)}
.rcard{display:flex;gap:12px;align-items:center;border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:6px 0;background:var(--panel)}
.rsvg{width:150px;height:50px;flex-shrink:0}
.place{margin:6px 0}
.zone{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0;background:var(--panel);break-inside:avoid}
.zone h4{margin:0 0 6px;font-size:12.5px;color:var(--acc)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid #3a4657;background:#1b2530;border-radius:5px;padding:2px 8px;font:10.5px Consolas,monospace;direction:ltr;unicode-bidi:embed;color:#dbe4ee}
.box{border:1px solid #5a4a1a;background:#241f16;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:12px;color:#e2c797}
.box b{color:#ffe1a6}
ol,ul{padding-right:20px}li{margin:4px 0}
.legend{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:var(--mut);margin:8px 0}
.legend span{display:inline-flex;align-items:center;gap:5px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
@media print{body{background:#fff;color:#111}.wrap{max-width:none;padding:0}h2,h3{color:#0b5394}.muted{color:#555}th{background:#eee;color:#333}td,th{border-color:#bbb}.rcard,.place,.box{background:#fafafa;border-color:#ccc}.place{break-before:page}.zone{background:transparent;border:0;padding:0;margin:10px 0;break-inside:auto}.zone h4{color:#0b5394}.chips{display:block}.chip{display:inline-block;margin:0 4px 4px 0;background:#e8ecf0;border-color:#999;color:#111}.wchip{color:#000!important;border-color:#666!important}.box{color:#5a4a1a}.box b{color:#7a5a00}}
</style></head><body><div class="wrap">
<h1>راهنمای ساخت و سیم‌کشی — ساعت دیجیتال CMOS (برای مبتدی)</h1>
<p class="sub">جای‌گذاری بلوکی همهٔ __NCOMP__ قطعه + سیم‌کشی کامل نت‌به‌نت + کد رنگ مقاومت‌ها و کد خازن‌ها. منبع: netlist.csv همین پروژه.</p>
<div class="box"><b>قبل از شروع:</b> این راهنما ترتیب و اتصالات را می‌دهد؛ ولتاژ/جریان آنالوگ و پایداری نهایی نیازمند تست روی برد است. ابتدا تغذیه را بساز و تست کن، بعد بلوک‌به‌بلوک جلو برو. همه پایه‌های VCC را به ریل +5V و همه GND را به ریل زمین وصل کن (در جدول‌های نت تکرار نشده‌اند).</div>
<h2>الف) شناسایی قطعات</h2>
<h3>مقاومت‌ها — کد رنگ ۴ نواری (±۵٪)</h3>
__RES__
<h3>خازن‌ها — کد روی بدنه و قطبیت</h3>
<table><tr><th>مقدار</th><th>کد روی بدنه</th><th>نوع</th><th>قطبیت</th><th>ولتاژ</th><th>تعداد</th></tr>__CAPS__</table>
<p class="muted">الکترولیت‌ها قطبی‌اند: نوار/علامت منفی روی بدنه = پایهٔ منفی (به GND). سرامیک/فیلم غیرقطبی‌اند. کدها: 104=100nF، 105=1µF، 334=0.33µF، 180=18pF.</p>
<h3>آی‌سیها و بقیه</h3>
<table><tr><th>Ref</th><th>نام/مدل</th><th>پکیج</th><th>نقش</th></tr>
<tr><td class="mono">U1</td><td>CD4060B</td><td>DIP-16</td><td>تقسیم‌کننده+اسیلاتور؛ فقط ۶ پایه وصل می‌شود</td></tr>
<tr><td class="mono">U2</td><td>CD4013B</td><td>DIP-14</td><td>دو فلیپ‌فلاپ D (÷۲ و SET)</td></tr>
<tr><td class="mono">U3..U8</td><td>CD4026B ×6</td><td>DIP-16</td><td>شمارنده+درایور ۷سگمنت</td></tr>
<tr><td class="mono">U9..U11</td><td>CD4081B ×3</td><td>DIP-14</td><td>چهار AND</td></tr>
<tr><td class="mono">U12..U13</td><td>CD4071B ×2</td><td>DIP-14</td><td>چهار OR</td></tr>
<tr><td class="mono">U14..U15</td><td>CD4093B ×2</td><td>DIP-14</td><td>اشمیت NAND (دیبانس/معکوس)</td></tr>
<tr><td class="mono">U16</td><td>7805</td><td>TO-220</td><td>رگولاتور ۵V</td></tr>
<tr><td class="mono">Q1</td><td>2N3904</td><td>TO-92</td><td>درایور کولن</td></tr>
<tr><td class="mono">DS1..DS6</td><td>SC52-11EWA</td><td>10-pin</td><td>نمایشگر کاتد-مشترک</td></tr>
<tr><td class="mono">Y1</td><td>کریستال 32.768kHz</td><td>HC-49S</td><td>مرجع فرکانس</td></tr>
<tr><td class="mono">D1 / D2</td><td>1N4007 / 1N4148</td><td>DO-41/DO-35</td><td>حفاظت ورودی / تخلیه POR</td></tr>
<tr><td class="mono">SW_*</td><td>کلید tact 6×6</td><td>4-pin</td><td>SET/HOUR/MIN/SECRST/MSTRST</td></tr>
<tr><td class="mono">LED1/2</td><td>LED قرمز 5mm</td><td>—</td><td>کولن</td></tr>
<tr><td class="mono">J1</td><td>جک DC</td><td>2-pin</td><td>ورودی ۹–۱۲V</td></tr></table>
<h2>ب) نقشه جای‌گذاری (بلوک‌به‌بلوک، به ترتیب مونتاژ)</h2>
<p class="muted">هر قطعه را در بلوک خودش بگذار. بای‌پس C_BYPn را چسبیده به پایه‌های VDD/VSS آی‌سی U n قرار بده. جهت پایهٔ ۱ هر IC را با نقطه/فرورفتگی بدنه و جدول نت تطبی بده.</p>
<div class="place">__PLACE__</div>
<h2>پ) رنگ سیم پیشنهادی</h2>
<div class="legend">
<span><i style="background:#e05252"></i>+5V (VCC)</span><span><i style="background:#9aa4b2"></i>زمین (GND)</span><span><i style="background:#f0883e"></i>ورودی تغذیه</span><span><i style="background:#b18cff"></i>کریستال</span><span><i style="background:#58a6ff"></i>کلاک</span><span><i style="background:#f778ba"></i>کلید/حالت</span><span><i style="background:#e3b341"></i>ریست/دیکود</span><span><i style="background:#7ee787"></i>کری</span><span><i style="background:#39c5cf"></i>سگمنت</span><span><i style="background:#d29922"></i>کولن</span></div>
<h2>ت) سیم‌کشی کامل نت‌به‌نت</h2>
<p class="muted">هر ردیف = یک نت الکتریکی: همه پایه‌های listed را با سیمِ همان رنگ به هم وصل کن (یک گره). VCC/GND/NC اینجا نیستند؛ VCC و GND را به ریل‌ها ببر (__NVCC__ پایه VCC و __NGND__ پایه GND). NC = بدون اتصال.</p>
__WIRE__
<h2>ث) ترتیب مونتاژ و تست مرحله‌ای</h2>
<ol>
<li>تغذیه: J1→D1→U16 + خازن‌های ورودی/خروجی + C_BULK. بدون بقیه مدار، خروجی U16 را اندازه بگیر: باید ≈۵V باشد.</li>
<li>ریل‌ها: +5V و GND را به همه پایه‌های VCC/VSS ببر (بای‌پس‌ها را کنار هر IC بگذار).</li>
<li>POR: R_POR/C_POR/D2 + گیت U15C. هنگام روشن‌شدن RST_GLOBAL باید ~۰٫۸۷s یک باشد سپس صفر.</li>
<li>پایه زمان: 4060 (۶ سیم) + شبکه کریستال + U2 + U15D. با اسیلوسکوپ/مولتی‌متر فرکانس Q14=2Hz و CLK1HZ=1Hz را چک کن.</li>
<li>گیت‌ها U9..U13 را سیم‌کشی کن؛ ورودی‌های استفاده‌نشده را شناور نگذار (به GND یا VCC طبق نت‌لیست).</li>
<li>کلیدها + دیبانس؛ هر کلید یک پالس تمیز بدهد.</li>
<li>رقم‌ها U3..U8 + مقاومت‌های سگمنت + نمایشگرها؛ هر رقم ۰..۹ را دستی کلاک بده و الگوی سگمنت را چک کن.</li>
<li>کولن Q1 + LEDها؛ با 1Hz چشمک بزند.</li>
<li>تست کامل: ۵۹→۶۰، ۵۹:۵۹→۱:۰۰، ۲۳:۵۹:۵۹→۰۰:۰۰:۰۰ و SET/ریست.</li>
</ol>
<div class="box"><b>4060 DIP-16:</b> فقط پایه‌های 16(+5V)، 8(GND)، 12(RST_GLOBAL=U13.3)، 3(Q14=U15.12&amp;13)، 11(XTAL_A)، 10(R_S.2) را وصل کن؛ بقیه باز. پایهٔ ۹ عمداً باز. جهت پایهٔ ۱ و شکاف سوکت را چک کن؛ پل‌قلع به پایهٔ مجاور ممنوع.</div>
<p class="sub">تولید خودکار از netlist.csv — __NCOMP__ قطعه، __NPIN__ پایه، __NNET__ نت قابل سیم‌کشی (به‌جز NC). این راهنما نقشهٔ ساخت است؛ تأیید نهایی سخت‌افزاری نیازمند تست روی برد واقعی است.</p>
</div></body></html>'''

ncomp = len(comps); npin = sum(len(c['pins']) for c in comps.values())
nnet = len([n for n in netdesc if n != 'NC'])
html = (HTML.replace('__RES__', ''.join(res_html)).replace('__CAPS__', ''.join(cap_rows))
        .replace('__PLACE__', PLACE).replace('__WIRE__', ''.join(wire_html))
        .replace('__NCOMP__', str(ncomp)).replace('__NPIN__', str(npin)).replace('__NNET__', str(nnet))
        .replace('__NVCC__', str(rails_vcc)).replace('__NGND__', str(rails_gnd)))
path = os.path.join(OUT, 'build_guide_fa.html')
with open(path, 'w', encoding='utf-8') as f: f.write(html)
print('wrote', path, len(html), 'bytes;', ncomp, 'components;', npin, 'pins;', nnet, 'nets')
print('resistor bands:', {v: [nm for _, nm in bands(v)] for v in RES_VALUES})
