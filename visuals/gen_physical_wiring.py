# -*- coding: utf-8 -*-
"""Point-to-point physical build map (wooden board + enamelled wire).
Emits physical_wiring.html (interactive, step-by-step) from the netlist via
board_layout (placement) + board_router (non-overlapping wires) + board_model (steps)."""
import json, os, sys, io
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from board_layout import RAILS, PHASES, W, H, G
from board_model import build_model, assign

COLORS_FA = ['سیاه', 'قهوه‌ای', 'قرمز', 'نارنجی', 'زرد', 'سبز', 'آبی', 'بنفش', 'خاکستری', 'سفید']
BANDS = {'470R': (4, 7, 1), '1k': (1, 0, 2), '10k': (1, 0, 3), '100k': (1, 0, 4), '220k': (2, 2, 4), '10M': (1, 0, 6)}
CODE = {'18pF': '18', '100nF': '104', '1uF': '105', '0.33uF': '334'}
RAIL_FA = {'GND_TOP': 'GND بالای نمایشگرها', 'VCC_D': '+5V زیر آی‌سی‌های ارقام', 'GND_D': 'GND زیر آی‌سی‌های ارقام',
           'VCC_A': '+5V ردیف گیت‌ها', 'GND_A': 'GND ردیف گیت‌ها', 'VCC_B': '+5V ردیف پایهٔ زمان',
           'GND_B': 'GND ردیف پایهٔ زمان', 'VCC_C': '+5V ردیف کلیدها', 'GND_C': 'GND ردیف کلیدها و تغذیه',
           'SPINE_VCC': 'ستون عمودی +5V (سمت چپ؛ همهٔ ریل‌های +5V را به هم وصل می‌کند)',
           'SPINE_GND': 'ستون عمودی GND (سمت راست؛ همهٔ ریل‌های GND را به هم وصل می‌کند)'}

def hint(p):
    k, v, ref = p['kind'], p['value'], p['ref']
    if k.startswith('DIP'):
        return ('آی‌سی %s با سوکت %s پایه. شکاف (نیم‌دایره) و نقطهٔ پایهٔ ۱ را دقیقاً مثل نقشه بگذار؛ در نمای رو شکاف سمت چپ است. '
                'اول سوکت را محکم کن و سیم‌ها را به پایه‌های سوکت لحیم کن؛ آی‌سی را آخر کار جا بزن.') % (p['model'], k[3:])
    if k == 'AX' and p['sub'] == 'res':
        b = BANDS[v]
        return 'مقاومت %s، ۱/۴ وات. نوارهای رنگی: %s، %s، %s، طلایی. جهت ندارد.' % (v, COLORS_FA[b[0]], COLORS_FA[b[1]], COLORS_FA[b[2]])
    if k == 'AX':
        return 'دیود %s. نوار روی بدنه = کاتد (K) = پایهٔ ۲؛ نوار را مثل نقشه سمت پایهٔ ۲ بگذار.' % p['model']
    if k == 'CAP':
        extra = ' حتماً نوع NP0/C0G.' if v == '18pF' else ''
        if ref.startswith('C_BYP'):
            return 'خازن بای‌پس 100nF (کد 104) کنار آی‌سی U%s. دو پایه‌اش مستقیم روی ریل +5V و ریل GND لحیم می‌شوند. جهت ندارد.' % ref[5:]
        return 'خازن %s (روی بدنه: %s). جهت ندارد.%s' % (v, CODE.get(v, v), extra)
    if k == 'ELEC':
        return 'خازن الکترولیتی %s. پایهٔ بلند (+) = پایهٔ ۱، سمت علامت + روی نقشه. نوار روشن روی بدنه = منفی. برعکس نصب نشود.' % v
    if k == 'LED':
        return 'LED قرمز کولن. پایهٔ بلند = آند (+) = پایهٔ ۱؛ لبهٔ صاف بدنه = کاتد = پایهٔ ۲.'
    if k == 'TO92':
        return 'ترانزیستور 2N3904. سطح صاف رو به پایین نقشه؛ در نمای رو از چپ: E (۱)، B (۲)، C (۳).'
    if k == 'TO220':
        return 'رگولاتور 7805. نوشته‌ها رو به پایین نقشه؛ در نمای رو از چپ: ۱ ورودی، ۲ زمین، ۳ خروجی ۵ ولت. بدون هیت‌سینک مشکلی ندارد.'
    if k == 'TACT':
        return 'کلید فشاری ۴پایه. فقط دو پایهٔ ضربدری ۱ و ۳ سیم می‌خورند (این روش همیشه درست است). پایهٔ ۱↔۲ و ۳↔۴ داخل کلید به هم وصل‌اند.'
    if k == 'DISP':
        return 'نمایشگر ۷ سگمنت کاتد مشترک SC52-11EWA. نقطهٔ اعشار پایین-راست باشد. پایه‌های ۳ و ۸ داخل به هم وصل‌اند؛ فقط پایهٔ ۸ سیم می‌خورد.'
    if k == 'XTAL':
        return 'کریستال ۳۲٫۷۶۸ کیلوهرتز. جهت ندارد. پایه‌هایش نازک‌اند؛ گرمای هویه را کوتاه نگه دار.'
    if k == 'TERM':
        return 'ورودی تغذیه ۹ تا ۱۲ ولت DC (جک یا ترمینال پیچی). پایهٔ ۱ = مثبت، پایهٔ ۲ = منفی.'
    return ''

def overlaps(conns, parts):
    """Independent check: no unit segment of the grid is used by two wires,
    except the two cells right at a pin that legitimately carries two wires."""
    use = defaultdict(list)
    for c in conns:
        if c.get('bridge'): continue
        pts = c['pts']
        cells = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            dx = (b[0] > a[0]) - (b[0] < a[0]); dy = (b[1] > a[1]) - (b[1] < a[1])
            x, y = a
            while (x, y) != tuple(b):
                x += dx; y += dy; cells.append((x, y))
        for i, (p, q) in enumerate(zip(cells, cells[1:])):
            near_end = min(i, len(cells) - 2 - i) < 2
            use[frozenset((tuple(p), tuple(q)))].append((c['id'], near_end, cells[0] if i < 2 else cells[-1]))
    bad = []
    for seg, us in use.items():
        if len(us) > 1 and not (all(u[1] for u in us) and len({u[2] for u in us}) == 1):
            bad.append((sorted(u[0] for u in us), sorted(seg)))
    return bad

def build():
    parts, conns, direct, joined, grid, relaxed, rows = build_model()
    steps = assign(parts, conns, direct)
    bad = overlaps(conns, parts)
    phase_of = {r: i for i, (t, refs) in enumerate(PHASES) for r in refs}
    for c in conns:
        if c.get('bridge'):
            p = parts[c['a']['ref']]
            c['bulge'] = -1 if c['a']['y'] < p['y'] else 1
    model = dict(
        W=W, H=H, G=G,
        parts=[dict(ref=p['ref'], kind=p['kind'], sub=p['sub'], rot=p['rot'], body=p['body'], model=p['model'],
                    value=p['value'], phase=phase_of[p['ref']],
                    pins={n: dict(x=q['x'], y=q['y'], name=q['name'], net=q['net']) for n, q in p['pins'].items()})
               for p in parts.values()],
        rails=[dict(name=n, net=net, o=o, f=f, s=s, e=e) for n, net, o, f, s, e in RAILS],
        railNames=RAIL_FA,
        wires=[dict(id=c['id'], net=c['net'], a=dict(ref=c['a']['ref'], pin=c['a']['pin']),
                    b=dict(ref=c['b']['ref'], pin=c['b']['pin']) if c['b'] else None, rail=c.get('rail'),
                    pts=[list(q) for q in c['pts']], len=c['steps'], color=c['color'], phase=c['phase'],
                    bridge=bool(c.get('bridge')), bulge=c.get('bulge', 0)) for c in conns],
        joined=joined, phases=[dict(title=t, parts=refs) for t, refs in PHASES],
        steps=steps, hints={p['ref']: hint(p) for p in parts.values()})
    return model, dict(errors=grid.errors, relaxed=relaxed, overlaps=bad, rows=rows, direct=len(direct))

def main():
    model, rep = build()
    tpl = open(os.path.join(HERE, 'physical_wiring_ui.html'), encoding='utf-8').read()
    js = lambda n: open(os.path.join(HERE, n), encoding='utf-8').read()
    html = (tpl.replace('__MODEL__', json.dumps(model, ensure_ascii=False, separators=(',', ':')))
            .replace('__DRAW__', js('pw_draw.js')).replace('__APP__', js('pw_app.js')))
    out = os.path.join(HERE, 'physical_wiring.html')
    open(out, 'w', encoding='utf-8').write(html)
    with open(os.path.join(HERE, 'physical_wiring_model.json'), 'w', encoding='utf-8') as f:
        json.dump(model, f, ensure_ascii=False)
    total = sum(w['len'] for w in model['wires']) * G / 1000
    print('wrote', out, len(html), 'bytes')
    print('parts %d wires %d (bridges %d) rails %d direct legs %d steps %d wire %.1f m' % (
        len(model['parts']), len(model['wires']), sum(w['bridge'] for w in model['wires']), len(model['rails']),
        rep['direct'], len(model['steps']), total))
    print('layout errors:', rep['errors'], '| relaxed:', rep['relaxed'], '| overlapping segments:', len(rep['overlaps']))
    if rep['overlaps']: print(rep['overlaps'][:10])

if __name__ == '__main__':
    main()
