# -*- coding: utf-8 -*-
"""Printable phase-by-phase build map.

Reads physical_wiring_model.json (written by gen_physical_wiring.py) and emits
physical_wiring_print.html: one A4-landscape page per build phase, rendered by
the same pw_draw.js as the interactive map. Keeping the renderer shared means
the print version can never drift away from the interactive model.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, 'physical_wiring_model.json')
OUT = os.path.join(HERE, 'physical_wiring_print.html')

FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def fa(n):
    return str(n).translate(FA_DIGITS)


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def main():
    with open(MODEL, encoding='utf-8') as f:
        model = json.load(f)
    draw = open(os.path.join(HERE, 'pw_draw.js'), encoding='utf-8').read()

    pages = []
    for i, phase in enumerate(model['phases']):
        refs = set(phase['parts'])
        xs, ys = [], []
        for part in model['parts']:
            if part['ref'] not in refs:
                continue
            x0, y0, x1, y1 = part['body']
            xs += [x0, x1]
            ys += [y0, y1]
        wires = [w for w in model['wires'] if w['phase'] == i]
        for wire in wires:
            for x, y in wire['pts']:
                xs.append(x)
                ys.append(y)
        if not xs:
            continue
        pad = 5
        x0, y0 = min(xs) - pad, min(ys) - pad
        x1, y1 = max(xs) + pad, max(ys) + pad
        pages.append(dict(
            phase=i, title=phase['title'], nparts=len(refs), nwires=len(wires),
            vb=(round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)),
        ))

    sections = []
    for n, page in enumerate(pages, 1):
        x, y, w, h = page['vb']
        i = page['phase']
        rows = []
        for wire in sorted([w for w in model['wires'] if w['phase'] == i], key=lambda w: w['id']):
            dst = ('%s.%s' % (wire['b']['ref'], wire['b']['pin'])) if wire['b'] else \
                ('ریل ' + model['railNames'].get(wire['rail'], wire['rail']))
            cut = round(wire['len'] * model['G'] + 15)
            rows.append('<tr><td class="w%d">%s</td><td dir="ltr">%s.%s</td><td dir="ltr">%s</td>'
                        '<td dir="ltr">%s</td><td dir="ltr">%s</td></tr>' % (
                            (int(wire['color'][1:6], 16) % 6) + 1, fa(wire['id']),
                            wire['a']['ref'], wire['a']['pin'], dst, esc(wire['net']), fa(cut) + ' mm'))
        test = next((s['text'] for s in model['steps'] if s['t'] == 'test' and s['ph'] == i), '')
        half = (len(rows) + 1) // 2
        tbl = lambda rs: '<table class="wt"><tr><th>سیم</th><th>از (پایه)</th><th>به (پایه/ریل)</th><th>نت</th><th>طول</th></tr>%s</table>' % ''.join(rs)
        tables = '<div class="two">' + tbl(rows[:half]) + (tbl(rows[half:]) if half < len(rows) else '') + '</div>'
        sections.append(
            '<section class="pg">'
            '<div class="ph"><span class="num">%s / %s</span><h2>%s</h2>'
            '<span class="meta">%s قطعه · %s سیم · کمرنگ: سایر بلوک‌ها</span></div>'
            '<div class="crop"><svg id="p%d" viewBox="%s %s %s %s" '
            'preserveAspectRatio="xMidYMid meet"></svg></div>'
            '%s'
            '<div class="test"><b>آزمایش این بخش:</b> %s</div>'
            '</section>' % (
                fa(n), fa(len(pages)), esc(page['title']), fa(page['nparts']),
                fa(page['nwires']), i, x, y, w, h, tables, esc(test),
            )
        )

    html = """<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>نقشهٔ فیزیکی و سیم‌کشی — نسخهٔ چاپی</title>
<style>
@page{size:A4 landscape;margin:7mm}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#111;font:12px Tahoma,"Segoe UI",sans-serif}
.pg{break-before:page;page-break-before:always;padding:0}
.pg:first-child{break-before:auto;page-break-before:auto}
.ph{display:flex;align-items:baseline;gap:10px;margin:0 0 3mm;direction:rtl}
.ph h2{font-size:15px;color:#0b5394;margin:0;font-weight:700}
.ph .num{font:700 11px Consolas,monospace;color:#fff;background:#0b5394;border-radius:4px;padding:2px 7px;direction:ltr}
.ph .meta{font-size:10.5px;color:#555;margin-right:auto}
.crop{height:92mm;border:1px solid #bbb;border-radius:5px;background:#f6f1e4;overflow:hidden}
.crop svg{width:100%;height:100%;display:block}
.two{display:flex;gap:3mm;margin-top:2mm}
.two table{flex:1}
.wt{width:100%;border-collapse:collapse;font:9.5px Tahoma}
.wt th,.wt td{border:1px solid #ccc;padding:0.6px 3px;text-align:center}
.wt th{background:#eef3f8}
.wt td[class^=w]{font-weight:700;color:#fff;background:#495057}
.wt td.w1{background:#c92a2a}.wt td.w2{background:#1864ab}.wt td.w3{background:#e8590c}
.wt td.w4{background:#2b8a3e}.wt td.w5{background:#862e9c}.wt td.w6{background:#5c6670}
.test{margin-top:1.5mm;border:1px dashed #2b8a3e;border-radius:5px;padding:1.5mm 3mm;font-size:10.5px;background:#f4fcf6}
.part.ghost{opacity:.16}
@media screen{body{background:#eceff3;padding:8mm}.pg{max-width:281mm;margin:0 auto 10mm;background:#fff;padding:4mm;border:1px solid #ccc;border-radius:6px}}
</style></head>
<body>
__SECTIONS__
<script>window.PW_MODEL=__MODEL__;</script>
<script>__DRAW__</script>
<script>
(function(){
  const M = window.PW_MODEL;
  const joined = {};
  M.joined.forEach(j => ((joined[j.ref] = joined[j.ref] || {})[j.pin] = j.to));
  PW.setJoined(joined);
  const pages = __PAGES__;
  pages.forEach(pg => {
    const svg = document.getElementById('p' + pg.phase);
    if (!svg) return;
    PW.render(M, svg, {
      ghost: p => p.phase !== pg.phase,
      hideGhost: true,
      hideWire: w => w.phase !== pg.phase
    });
  });
})();
</script>
</body></html>"""
    html = (html
            .replace('__SECTIONS__', '\n'.join(sections))
            .replace('__MODEL__', json.dumps(model, ensure_ascii=False, separators=(',', ':')))
            .replace('__DRAW__', draw)
            .replace('__PAGES__', json.dumps([{'phase': p['phase']} for p in pages], ensure_ascii=False)))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('wrote', OUT, len(html), 'bytes;', len(pages), 'pages')


if __name__ == '__main__':
    main()
