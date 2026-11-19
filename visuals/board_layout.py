# -*- coding: utf-8 -*-
"""Physical board layout for a point-to-point (enamelled wire) build.
Grid unit g = 1.27 mm; every pin lands on an integer grid point."""
import csv, os
from itertools import permutations

HERE = os.path.dirname(os.path.abspath(__file__))
G = 1.27
W, H = 214, 144

def fp(kind, span=4):
    if kind in ('DIP14', 'DIP16'):
        n = int(kind[3:]); h = n // 2; d = {}
        for k in range(1, h + 1):
            x = -(h - 1) + 2 * (k - 1); d[k] = (x, 3); d[n + 1 - k] = (x, -3)
        return d
    if kind == 'DISP':
        d = {p: (-4 + 2 * i, -6) for i, p in enumerate((10, 9, 8, 7, 6))}
        d.update({p: (-4 + 2 * i, 6) for i, p in enumerate((1, 2, 3, 4, 5))})
        return d
    if kind == 'TACT': return {1: (0, 0), 2: (5, 0), 3: (5, 4), 4: (0, 4)}
    if kind in ('TO92', 'TO220'): return {1: (0, 0), 2: (2, 0), 3: (4, 0)}
    return {1: (0, 0), 2: (span, 0)}

def body(kind, span, sub=''):
    s = span / 2
    if kind in ('DIP14', 'DIP16'): h = int(kind[3:]) // 2; return (-h, -2.3, h, 2.3)
    if kind == 'DISP': return (-5, -7.5, 5, 7.5)
    if kind == 'TACT': return (0.15, 0.4, 4.85, 3.6)
    if kind == 'AX':
        L, R = {'res': (2.5, 0.95), 'do35': (1.6, 0.75), 'do41': (2.05, 1.05)}[sub]
        return (s - L, -R, s + L, R)
    if kind == 'CAP':
        a = min(2, s - 0.6); return (s - a, -3.4, s + a, -0.6)
    if kind == 'ELEC':
        r = {'10uF': 2.0, '100uF': 2.5, '470uF': 3.2}[sub]; return (s - r, -2 * r - 0.5, s + r, -0.5)
    if kind == 'XTAL': return (s - 0.8, -5.4, s + 0.8, -0.6)
    if kind == 'LED': return (s - 2.3, -5.2, s + 2.3, -0.6)
    if kind == 'TO92': return (-0.4, -3.2, 4.4, -0.6)
    if kind == 'TO220': return (-1.9, -3.8, 5.9, -0.4)
    if kind == 'TERM': return (-1.9, -5.5, 5.9, -0.6)
    raise KeyError(kind)

def rot(p, r):
    x, y = p
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[r]

def rot_rect(b, r):
    a = rot((b[0], b[1]), r); c = rot((b[2], b[3]), r)
    return (min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1]))

def load_netlist():
    rows = list(csv.DictReader(open(os.path.join(HERE, '..', 'netlist', 'netlist.csv'), encoding='utf-8-sig')))
    info = {}
    for r in rows:
        d = info.setdefault(r['Ref'], {'model': r['Model'], 'value': r['Value'], 'pkg': r['Package'], 'pins': {}})
        d['pins'][int(r['Pin'])] = (r['PinName'], r['Net'])
    return info

DIGITS = [('HT', 'U8', 'DS1', 20), ('HU', 'U7', 'DS2', 50), ('MT', 'U6', 'DS3', 88),
          ('MU', 'U5', 'DS4', 118), ('ST', 'U4', 'DS5', 156), ('SU', 'U3', 'DS6', 186)]
SEG_DX = {'G': -12, 'F': -8, 'E': -4, 'D': 0, 'C': 4, 'A': 8, 'B': 12}
RAILS = [  # name, net, orient, fixed, start, end
    ('GND_TOP', 'GND', 'h', 3, 8, 211), ('VCC_D', 'VCC', 'h', 57, 3, 207), ('GND_D', 'GND', 'h', 60, 8, 211),
    ('VCC_A', 'VCC', 'h', 66, 3, 207), ('GND_A', 'GND', 'h', 78, 8, 211), ('VCC_B', 'VCC', 'h', 84, 3, 207),
    ('GND_B', 'GND', 'h', 96, 8, 211), ('VCC_C', 'VCC', 'h', 122, 3, 170), ('GND_C', 'GND', 'h', 138, 20, 211),
    ('SPINE_VCC', 'VCC', 'v', 3, 57, 122), ('SPINE_GND', 'GND', 'v', 211, 3, 138)]
ROW_A_SLOTS = [26, 62, 98, 134, 170]
ROW_B_SLOTS = [46, 82, 118]
BTN_X = {'SET': 76, 'HOUR': 96, 'MIN': 116, 'SECRST': 136, 'MSTRST': 156}

def placements(row_a, row_b):
    P = {}
    def put(ref, kind, x, y, r=0, span=4, sub=''): P[ref] = dict(kind=kind, x=x, y=y, rot=r, span=span, sub=sub)
    for dig, u, ds, cx in DIGITS:
        put(ds, 'DISP', cx, 16)
        for s, dx in SEG_DX.items(): put('R_%s%s' % (dig, s), 'AX', cx + dx, 36, 270, 8, 'res')
        put(u, 'DIP16', cx, 50)
        put('C_BYP%d' % int(u[1:]), 'CAP', cx + 11, 57, 90, 3)
    for u, x in zip(row_a, ROW_A_SLOTS):
        put(u, 'DIP14', x, 72); put('C_BYP%d' % int(u[1:]), 'CAP', x + 10, 66, 90, 12)
    put('U1', 'DIP16', 20, 90); put('C_BYP1', 'CAP', 8, 84, 90, 12)
    for u, x in zip(row_b, ROW_B_SLOTS):
        put(u, 'DIP14', x, 90); put('C_BYP%d' % int(u[1:]), 'CAP', x + 10, 84, 90, 12)
    put('R_C', 'AX', 8, 104, 0, 8, 'res'); put('R_S', 'AX', 28, 104, 0, 8, 'res')
    put('Y1', 'XTAL', 20, 110, 0, 2); put('C1', 'CAP', 8, 110, 90, 4); put('C2', 'CAP', 30, 110, 90, 4)
    put('R_POR', 'AX', 52, 122, 270, 8, 'res'); put('C_POR', 'ELEC', 56, 112, 0, 2, '10uF')
    put('D2', 'AX', 60, 116, 0, 6, 'do35')
    put('LED1', 'LED', 68, 17, 0, 2); put('LED2', 'LED', 136, 17, 0, 2)
    put('R_CL1', 'AX', 66, 34, 270, 8, 'res'); put('R_CL2', 'AX', 140, 34, 270, 8, 'res')
    put('Q1', 'TO92', 66, 48); put('R_CB', 'AX', 72, 40, 90, 8, 'res')
    for n, x in BTN_X.items():
        put('R_PU_' + n, 'AX', x, 122, 90, 8, 'res'); put('C_BTN_' + n, 'CAP', x + 4, 134, 90, 4)
        put('SW_' + n, 'TACT', x + 8, 134)
    put('J1', 'TERM', 16, 138); put('D1', 'AX', 6, 128, 0, 8, 'do41'); put('U16', 'TO220', 24, 128)
    put('C_IN1', 'CAP', 34, 133, 90, 5); put('C_IN2', 'ELEC', 38, 135, 0, 2, '100uF')
    put('C_OUT1', 'CAP', 46, 133, 90, 5); put('C_OUT2', 'ELEC', 50, 135, 0, 2, '100uF')
    put('C_BULK', 'ELEC', 58, 135, 0, 4, '470uF')
    return P

PHASES = [
    ('تغذیه و ریل‌ها', ['J1', 'D1', 'U16', 'C_IN1', 'C_IN2', 'C_OUT1', 'C_OUT2', 'C_BULK']),
    ('ریست روشن‌شدن و کلید ریست کل', ['R_POR', 'C_POR', 'D2', 'U15', 'C_BYP15', 'U13', 'C_BYP13', 'SW_MSTRST', 'R_PU_MSTRST', 'C_BTN_MSTRST']),
    ('پایهٔ زمان (کریستال و تقسیم)', ['U1', 'C_BYP1', 'Y1', 'C1', 'C2', 'R_C', 'R_S', 'U2', 'C_BYP2']),
    ('کولن چشمک‌زن', ['Q1', 'R_CB', 'R_CL1', 'R_CL2', 'LED1', 'LED2']),
    ('کلیدها و دیبانس', ['U14', 'C_BYP14'] + [p + n for n in ('SET', 'HOUR', 'MIN', 'SECRST') for p in ('SW_', 'R_PU_', 'C_BTN_')]),
    ('گیت‌های منطقی', ['U9', 'U10', 'U11', 'U12', 'C_BYP9', 'C_BYP10', 'C_BYP11', 'C_BYP12']),
] + [('رقم ' + d, [u, 'C_BYP%d' % int(u[1:]), ds] + ['R_%s%s' % (d, s) for s in 'ABCDEFG'])
     for d, u, ds, cx in [DIGITS[5], DIGITS[4], DIGITS[3], DIGITS[2], DIGITS[1], DIGITS[0]]]

def build_parts(info, row_a, row_b):
    P = placements(row_a, row_b)
    parts = {}
    for ref, p in P.items():
        off = fp(p['kind'], p['span'])
        pins = {}
        for n, (dx, dy) in off.items():
            rx, ry = rot((dx, dy), p['rot'])
            name, net = info[ref]['pins'][n]
            pins[n] = dict(x=p['x'] + rx, y=p['y'] + ry, name=name, net=net)
        b = rot_rect(body(p['kind'], p['span'], p['sub']), p['rot'])
        parts[ref] = dict(p, ref=ref, pins=pins, body=(p['x'] + b[0], p['y'] + b[1], p['x'] + b[2], p['y'] + b[3]),
                          model=info[ref]['model'], value=info[ref]['value'])
    return parts

def hpwl(parts):
    nets = {}
    for p in parts.values():
        for q in p['pins'].values():
            if q['net'] not in ('NC', 'VCC', 'GND'): nets.setdefault(q['net'], []).append((q['x'], q['y']))
    return sum(max(x for x, _ in v) - min(x for x, _ in v) + max(y for _, y in v) - min(y for _, y in v) for v in nets.values())

def best_layout(info):
    best = None
    for ra in permutations(['U9', 'U10', 'U11', 'U12', 'U13']):
        for rb in permutations(['U2', 'U14', 'U15']):
            c = hpwl(build_parts(info, ra, rb))
            if best is None or c < best[0]: best = (c, ra, rb)
    return best

if __name__ == '__main__':
    info = load_netlist()
    c, ra, rb = best_layout(info)
    parts = build_parts(info, ra, rb)
    missing = set(info) - set(parts)
    print('row A', ra, 'row B', rb, 'HPWL', c, 'parts', len(parts), 'missing', sorted(missing))
