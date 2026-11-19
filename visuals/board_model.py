# -*- coding: utf-8 -*-
"""Builds the board model: placement + routed wires + ordered build steps."""
import csv, os
from board_layout import load_netlist, best_layout, build_parts, RAILS, PHASES, W, H, G, HERE
from board_router import Grid, simplify, chain, JOINED, cid

PALETTE = ['#ff6b6b', '#4dabf7', '#ffd43b', '#69db7c', '#da77f2', '#ff922b',
           '#38d9a9', '#f783ac', '#a9e34b', '#74c0fc', '#ffa8a8', '#e599f7']

TESTS = [
    'آداپتور ۹ تا ۱۲ ولت را وصل کن. با مولتی‌متر بین ریل VCC و GND باید حدود ۵ ولت (۴٫۷۵ تا ۵٫۲۵) ببینی. اگر نبود فوراً قطع کن و جهت D1 و پایه‌های 7805 را چک کن.',
    'بعد از روشن‌کردن، پایهٔ ۳ آی‌سی U13 حدود یک ثانیه نزدیک ۵ ولت و بعد نزدیک ۰ ولت می‌شود؛ با فشار کلید MASTER RESET دوباره ۵ ولت می‌شود. در این مرحله فقط همین پایه را بسنج (ورودی‌های هنوز وصل‌نشده ممکن است بقیهٔ گیت‌ها را بی‌قرار کنند).',
    'آزمون این مرحله در مرحلهٔ بعد (کولن) دیده می‌شود. اگر اسیلوسکوپ داری: پایهٔ ۳ آی‌سی U1 باید ۲ هرتز و پایهٔ ۱ آی‌سی U2 باید ۱ هرتز باشد.',
    'هر دو LED کولن باید هر ثانیه یک بار چشمک بزنند (نیم ثانیه روشن، نیم ثانیه خاموش). اگر نزدند، اول پایهٔ ۱ آی‌سی U2 و بعد جهت LEDها و پایه‌های Q1 را چک کن.',
    'با فشردن هر کلید، پایهٔ خروجی متناظر U14 (۳ برای SET، ۴ برای HOUR+، ۱۰ برای MIN+، ۱۱ برای SEC RESET) از حدود ۰ به حدود ۵ ولت می‌رود و با رهاکردن برمی‌گردد.',
    'این گیت‌ها آزمون جداگانه ندارند؛ در مراحل ارقام آزمایش می‌شوند.',
    'رقم یکان ثانیه باید هر ثانیه یکی زیاد شود: ۰ تا ۹ و دوباره ۰.',
    'ثانیه‌ها باید از 00 تا 59 بشمارند و بعد از 59 به 00 برگردند. کلید SEC RESET ثانیه‌ها را صفر می‌کند.',
    'بعد از هر 59 ثانیه، یکان دقیقه یکی زیاد می‌شود. تنظیم: SET را بزن، با MIN+ دقیقه را زیاد کن، دوباره SET.',
    'دقیقه‌ها باید از 00 تا 59 بشمارند و بعد از 59 به 00 برگردند.',
    'بعد از 59:59 یکان ساعت زیاد می‌شود. تنظیم: SET، سپس HOUR+، دوباره SET.',
    'تست کامل: SET را بزن، با HOUR+ ساعت را 23 و با MIN+ دقیقه را 59 کن، دوباره SET. حداکثر یک دقیقه بعد باید 00:00:00 نمایش داده شود. MASTER RESET همه را 00:00:00 می‌کند.',
]

def build_model():
    info = load_netlist()
    _, ra, rb = best_layout(info)
    parts = build_parts(info, ra, rb)
    grid = Grid(parts, RAILS)
    phase_of = {r: i for i, (t, refs) in enumerate(PHASES) for r in refs}
    assert set(parts) == set(phase_of), set(parts) ^ set(phase_of)
    nets, direct, joined, conns = {}, [], [], []
    for p in parts.values():
        jm = JOINED.get(p['kind'], {})
        for n, q in p['pins'].items():
            if q['net'] == 'NC': continue
            if n in jm: joined.append(dict(ref=p['ref'], pin=n, to=jm[n])); continue
            nets.setdefault(q['net'], []).append(dict(ref=p['ref'], pin=n, x=q['x'], y=q['y']))
    bridges = []
    for net, nodes in nets.items():
        keep = []
        for nd in nodes:
            mate = next((k for k in keep if k['ref'] == nd['ref'] and parts[nd['ref']]['kind'].startswith('DIP')
                         and abs(k['x'] - nd['x']) + abs(k['y'] - nd['y']) == 2), None)
            if mate:
                bridges.append(dict(net=net, a=mate, b=nd, bridge=True, pts=[(mate['x'], mate['y']), (nd['x'], nd['y'])], steps=2))
                continue
            keep.append(nd)
        nets[net] = keep
    shapes, cells = {'VCC': [], 'GND': []}, {'VCC': set(), 'GND': set()}
    for name, net, o, f, s, e in RAILS:
        shapes[net].append((o, f, s, e))
        for t in range(s, e + 1): cells[net].add(cid(*((t, f) if o == 'h' else (f, t))))
    for net, nodes in nets.items():
        if net in ('VCC', 'GND'):
            for nd in nodes:
                c = cid(nd['x'], nd['y'])
                if c in grid.rail and grid.rail[c][0] == net:
                    direct.append(dict(nd, net=net, rail=grid.rail[c][2]))
                else: conns.append(dict(net=net, a=nd, b=None))
        else:
            order = chain(nodes, lambda nd: parts[nd['ref']]['kind'] in ('DIP14', 'DIP16', 'DISP'))
            conns += [dict(net=net, a=a, b=b) for a, b in zip(order, order[1:])]

    def est(c):
        a = c['a']
        if c['b'] is None:
            return min(abs(a['y'] - f) + max(0, s - a['x'], a['x'] - e) if o == 'h'
                       else abs(a['x'] - f) + max(0, s - a['y'], a['y'] - e) for o, f, s, e in shapes[c['net']])
        return abs(a['x'] - c['b']['x']) + abs(a['y'] - c['b']['y'])
    conns.sort(key=est)
    from collections import Counter
    deg = Counter(cid(e['x'], e['y']) for c in conns for e in (c['a'], c['b']) if e is not None)
    grid.deg2 = {k for k, v in deg.items() if v >= 2}
    relaxed = []
    for c in conns:
        a = c['a']
        if c['b'] is None:
            goal = {q for q in cells[c['net']] if not grid.lock[q] and q not in grid.pin}
            args = ((a['x'], a['y']), goal, shapes[c['net']], c['net'])
        else:
            b = c['b']
            args = ((a['x'], a['y']), {cid(b['x'], b['y'])}, [('pt', b['x'], b['y'])], c['net'])
        path = grid.route(*args)
        if path is None:
            path = grid.route(*args, relax=True); relaxed.append(c['net'])
        grid.commit(path, c['b'] is None)
        c['pts'] = simplify(path); c['steps'] = len(path) - 1
        if c['b'] is None: c['rail'] = grid.rail[cid(*path[-1])][2]
    conns += bridges
    for c in conns:
        ph = phase_of[c['a']['ref']]
        if c['b'] is not None: ph = max(ph, phase_of[c['b']['ref']])
        c['phase'] = ph
    return parts, conns, direct, joined, grid, relaxed, (ra, rb)

def bbox(pts, m=3):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)

def assign(parts, conns, direct):
    """Order wires by phase, number them, colour them so neighbours differ, list build steps."""
    conns.sort(key=lambda c: (c['phase'], c['b'] is not None, min(p[0] for p in c['pts']), min(p[1] for p in c['pts'])))
    done = []
    for i, c in enumerate(conns, 1):
        c['id'] = i
        bb = bbox(c['pts'])
        near = [d['color'] for d in done if not (d['bb'][2] < bb[0] or bb[2] < d['bb'][0] or d['bb'][3] < bb[1] or bb[3] < d['bb'][1])]
        c['color'] = min(PALETTE, key=lambda col: (near.count(col), PALETTE.index(col)))
        c['bb'] = bb; done.append(c)
    steps = []
    for ph, (title, refs) in enumerate(PHASES):
        if ph == 0:
            steps += [dict(t='rail', ph=0, rail=r[0]) for r in RAILS]
        for r in refs:
            steps.append(dict(t='part', ph=ph, ref=r, direct=[dict(pin=d['pin'], rail=d['rail']) for d in direct if d['ref'] == r]))
        steps += [dict(t='wire', ph=ph, id=c['id']) for c in conns if c['phase'] == ph]
        steps.append(dict(t='test', ph=ph, text=TESTS[ph]))
    return steps

if __name__ == '__main__':
    import time
    t = time.time()
    parts, conns, direct, joined, grid, relaxed, rows = build_model()
    steps = assign(parts, conns, direct)
    L = sum(c['steps'] for c in conns) * G
    print('errors:', grid.errors)
    print('rows', rows, 'wires', len(conns), 'direct legs', len(direct), 'joined', len(joined))
    print('relaxed (overlap allowed):', len(relaxed), relaxed)
    print('total wire length %.1f m, steps %d, %.1fs' % (L / 1000, len(steps), time.time() - t))
