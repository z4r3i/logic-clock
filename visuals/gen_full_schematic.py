# -*- coding: utf-8 -*-
"""Generate the COMPLETE circuit schematic (interactive SVG) from netlist.csv.
Every component is drawn exactly once with real pin numbers; local wiring is
drawn as real wires, inter-region connections use same-name net tags (standard
schematic convention) plus click-to-trace highlighting across the whole sheet.
Outputs: circuit_schematic.html (standalone) + circuit_schematic_frag.html.
"""
import csv, os, io, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(OUT, '..', 'netlist', 'netlist.csv')
NETS_CSV = os.path.join(OUT, '..', 'netlist', 'nets.csv')

# ---------------- load netlist ----------------
comps = {}
with open(NETLIST, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ref = r['Ref']
        if ref not in comps:
            comps[ref] = {'model': r['Model'], 'value': r['Value'], 'pkg': r['Package'], 'pins': {}}
        comps[ref]['pins'][r['Pin']] = (r['PinName'], r['Net'], r['Notes'])
netdesc = {}
with open(NETS_CSV, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        netdesc[r['Net']] = r['Description']

def pnet(ref, pin):
    return comps[ref]['pins'][str(pin)][1]

def net_color(n):
    if n == 'VCC': return '#ff6b6b'
    if n == 'GND': return '#9aa4b2'
    if n in ('VIN', 'VIN2'): return '#ffa657'
    if n in ('XTAL_A', 'XTAL_B', 'OSC_FB'): return '#d2a8ff'
    if n.startswith('SEG_') or n.startswith('DSP_'): return '#39c5cf'
    if n.startswith('RST_') or n.startswith('POR_') or n in ('D24', 'D6_ST', 'D6_MT', 'HT2', 'HU4', 'ST_EF', 'MT_EF', 'HT_AD', 'HU_CF'): return '#f0883e'
    if n in ('C_SU', 'C_MU', 'C_HU'): return '#7ee787'
    if n.startswith('CLK') or n in ('FF1_D', 'FF2_D'): return '#79c0ff'
    if n.startswith('BTN') or n in ('SET_MODE', 'nSET_MODE', 'HOUR_GATE', 'MIN_GATE'): return '#f778ba'
    if n.startswith('COLON'): return '#e3b341'
    return '#6e7681'

SHEET_W, SHEET_H = 2600, 3040

REGIONS = [
    {'id': 'power', 'title': '\u062a\u063a\u0630\u06cc\u0647', 'x': 40, 'y': 60, 'w': 760, 'h': 470},
    {'id': 'por', 'title': '\u0631\u06cc\u0633\u062a \u0631\u0648\u0634\u0646\u200c\u0634\u062f\u0646 (POR)', 'x': 40, 'y': 570, 'w': 760, 'h': 430},
    {'id': 'btn', 'title': '\u062f\u06a9\u0645\u0647\u200c\u0647\u0627 \u0648 \u062f\u06cc\u0628\u0627\u0646\u0633', 'x': 40, 'y': 1040, 'w': 760, 'h': 1060},
    {'id': 'tb', 'title': '\u067e\u0627\u06cc\u0647 \u0632\u0645\u0627\u0646', 'x': 840, 'y': 60, 'w': 1720, 'h': 600},
    {'id': 'gates', 'title': '\u06af\u06cc\u062a\u200c\u0647\u0627\u06cc \u062f\u06cc\u06a9\u0648\u062f \u0648 \u0645\u0633\u06cc\u0631\u062f\u0647\u06cc', 'x': 840, 'y': 700, 'w': 1720, 'h': 960},
    {'id': 'colon', 'title': '\u062f\u0631\u0627\u06cc\u0648\u0631 \u06a9\u0648\u0644\u0646', 'x': 840, 'y': 1700, 'w': 1720, 'h': 400},
    {'id': 'cnt', 'title': '\u0634\u0645\u0627\u0631\u0646\u062f\u0647\u200c\u0647\u0627 \u0648 \u0646\u0645\u0627\u06cc\u0634\u06af\u0631\u0647\u0627 (HH:MM:SS)', 'x': 40, 'y': 2140, 'w': 2520, 'h': 800},
]

# ---------------- SVG builder ----------------
class Sch:
    def __init__(self):
        self.bg, self.wire_els, self.comp_els, self.tag_els = [], [], [], []
        self.pins, self.tags, self.wires = [], [], []
        self.drawn = set()

    def pin(self, ref, pin, x, y):
        name, net, note = comps[ref]['pins'][str(pin)]
        self.drawn.add((ref, str(pin)))
        self.pins.append({'ref': ref, 'pin': str(pin), 'name': name, 'net': net, 'x': round(x, 1), 'y': round(y, 1)})
        return (x, y)

    def stub(self, x1, y1, x2, y2, net):
        self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2" class="stub" data-net="%s"/>' % (x1, y1, x2, y2, net_color(net), net))

    def wire(self, net, pts, dots=()):
        self.wires.append({'net': net, 'pts': [[round(x, 1), round(y, 1)] for x, y in pts]})
        pstr = ' '.join('%.1f,%.1f' % (x, y) for x, y in pts)
        self.wire_els.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" class="w" data-net="%s"/>' % (pstr, net_color(net), net))
        for x, y in dots:
            self.wire_els.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="%s" class="w" data-net="%s"/>' % (x, y, net_color(net), net))

    def tag(self, net, x, y, anchor='start'):
        w = 7.0 * len(net) + 14
        rx = x if anchor == 'start' else (x - w if anchor == 'end' else x - w / 2)
        col = net_color(net)
        dash = ' stroke-dasharray="3 2"' if net == 'NC' else ''
        self.tag_els.append('<g class="tag" data-net="%s"><rect x="%.1f" y="%.1f" width="%.1f" height="20" rx="4" fill="#0d1117" stroke="%s"%s/><text x="%.1f" y="%.1f" fill="%s" font-size="10.5" font-family="Consolas,monospace" text-anchor="middle">%s</text></g>' % (net, rx, y - 10, w, col, dash, rx + w / 2, y + 3.5, col, net))
        self.tags.append({'net': net, 'x': round(rx + w / 2, 1), 'y': round(y, 1)})

    def text(self, x, y, s, size=12, fill='#c9d1d9', anchor='start', weight='normal', family=None):
        fam = ' font-family="%s"' % family if family else ''
        self.comp_els.append('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s" font-weight="%s"%s>%s</text>' % (x, y, size, fill, anchor, weight, fam, s))

    def region(self, r):
        self.bg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="#10151c" stroke="#263041" stroke-width="1.5"/>' % (r['x'], r['y'], r['w'], r['h']))
        self.bg.append('<text x="%d" y="%d" font-size="16" fill="#58a6ff" font-weight="bold" text-anchor="start">%s</text>' % (r['x'] + 18, r['y'] + 28, r['title']))

    # ---- generic DIP IC (pins in physical order) ----
    def dip(self, ref, x, y, w, left, right, wired=(), pitch=36):
        n = max(len(left), len(right))
        h = (n - 1) * pitch + 80
        model = comps[ref]['model']
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s (%s)</title><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="#161b22" stroke="#30363d" stroke-width="1.5"/><path d="M %.1f %.1f a 10 10 0 0 0 20 0" fill="none" stroke="#30363d" stroke-width="1.5"/>' % (ref, ref, model, comps[ref]['pkg'], x, y, w, h, x + w / 2 - 10, y))
        self.text(x + w / 2, y + 20, ref, 13, '#e6edf3', 'middle', 'bold')
        self.text(x + w / 2, y + 34, model, 9.5, '#8b949e', 'middle')
        for i, p in enumerate(left):
            py = y + 40 + i * pitch
            net = pnet(ref, p)
            self.stub(x, py, x - 24, py, net)
            self.pin(ref, p, x - 24, py)
            self.text(x + 7, py + 3, str(p), 8, '#6e7681')
            self.text(x + 22, py + 3, comps[ref]['pins'][str(p)][0], 8.5, '#8b949e')
            if p not in wired:
                self.tag(net, x - 30, py, 'end')
        for i, p in enumerate(right):
            py = y + 40 + i * pitch
            net = pnet(ref, p)
            self.stub(x + w, py, x + w + 24, py, net)
            self.pin(ref, p, x + w + 24, py)
            self.text(x + w - 7, py + 3, str(p), 8, '#6e7681', 'end')
            self.text(x + w - 22, py + 3, comps[ref]['pins'][str(p)][0], 8.5, '#8b949e', 'end')
            if p not in wired:
                self.tag(net, x + w + 30, py, 'start')
        self.comp_els.append('</g>')
        return h

    # ---- passives ----
    def res_v(self, ref, x, y):
        val = comps[ref]['value']
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, val))
        self.stub(x, y, x, y + 10, pnet(ref, 1)); self.stub(x, y + 50, x, y + 60, pnet(ref, 2))
        self.comp_els.append('<rect x="%.1f" y="%.1f" width="14" height="40" fill="none" stroke="#8b949e" stroke-width="1.5"/>' % (x - 7, y + 10))
        self.text(x + 12, y + 24, ref, 8.5, '#8b949e'); self.text(x + 12, y + 38, val, 9, '#c9d1d9')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x, y + 60)
        self.comp_els.append('</g>')

    def res_h(self, ref, x, y):
        val = comps[ref]['value']
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, val))
        self.stub(x, y, x + 18, y, pnet(ref, 1)); self.stub(x + 62, y, x + 80, y, pnet(ref, 2))
        self.comp_els.append('<rect x="%.1f" y="%.1f" width="44" height="14" fill="none" stroke="#8b949e" stroke-width="1.5"/>' % (x + 18, y - 7))
        self.text(x + 40, y - 13, ref, 8.5, '#8b949e', 'middle'); self.text(x + 40, y + 21, val, 9, '#c9d1d9', 'middle')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x + 80, y)
        self.comp_els.append('</g>')

    def cap_v(self, ref, x, y, pol=False):
        val = comps[ref]['value']
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, val))
        self.stub(x, y, x, y + 16, pnet(ref, 1)); self.stub(x, y + 26, x, y + 44, pnet(ref, 2))
        self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/>' % (x - 12, y + 16, x + 12, y + 16))
        if pol:
            self.comp_els.append('<path d="M %.1f %.1f Q %.1f %.1f %.1f %.1f" fill="none" stroke="#8b949e" stroke-width="2"/>' % (x - 12, y + 26, x, y + 32, x + 12, y + 26))
            self.text(x - 17, y + 12, '+', 10, '#8b949e')
        else:
            self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/>' % (x - 12, y + 26, x + 12, y + 26))
        self.text(x + 17, y + 18, ref, 8.5, '#8b949e'); self.text(x + 17, y + 32, val, 9, '#c9d1d9')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x, y + 44)
        self.comp_els.append('</g>')

    def diode_h(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, comps[ref]['model']))
        self.stub(x, y, x + 12, y, pnet(ref, 1)); self.stub(x + 30, y, x + 42, y, pnet(ref, 2))
        self.comp_els.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="none" stroke="#8b949e" stroke-width="1.5"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/>' % (x + 12, y - 9, x + 12, y + 9, x + 30, y, x + 30, y - 9, x + 30, y + 9))
        self.text(x + 21, y - 14, ref, 8.5, '#8b949e', 'middle'); self.text(x + 21, y + 22, comps[ref]['model'], 8.5, '#c9d1d9', 'middle')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x + 42, y)
        self.comp_els.append('</g>')

    def diode_v_up(self, ref, x, y):
        # cathode (pin2) at top (x,y), anode (pin1) at bottom (x,y+42)
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, comps[ref]['model']))
        self.stub(x, y, x, y + 12, pnet(ref, 2)); self.stub(x, y + 30, x, y + 42, pnet(ref, 1))
        self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/><path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="none" stroke="#8b949e" stroke-width="1.5"/>' % (x - 9, y + 12, x + 9, y + 12, x - 9, y + 30, x + 9, y + 30, x, y + 12))
        self.text(x - 14, y + 20, ref, 8.5, '#8b949e', 'end'); self.text(x - 14, y + 34, comps[ref]['model'], 8.5, '#c9d1d9', 'end')
        self.pin(ref, 2, x, y); self.pin(ref, 1, x, y + 42)
        self.comp_els.append('</g>')

    def led_v_down(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, comps[ref]['model']))
        self.stub(x, y, x, y + 12, pnet(ref, 1)); self.stub(x, y + 30, x, y + 42, pnet(ref, 2))
        self.comp_els.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="none" stroke="#e3b341" stroke-width="1.5"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e3b341" stroke-width="2"/>' % (x - 9, y + 12, x + 9, y + 12, x, y + 30, x - 9, y + 30, x + 9, y + 30))
        for dx in (0, 9):
            self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e3b341" stroke-width="1.2"/><path d="M %.1f %.1f l -5 -1 l 3 4 Z" fill="#e3b341"/>' % (x + 13 + dx, y + 12 + dx, x + 20 + dx, y + 19 + dx, x + 20 + dx, y + 19 + dx))
        self.text(x + 26, y + 18, ref, 8.5, '#8b949e'); self.text(x + 26, y + 32, 'LED', 8.5, '#c9d1d9')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x, y + 42)
        self.comp_els.append('</g>')

    def xtal_h(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, comps[ref]['model']))
        self.stub(x, y, x + 8, y, pnet(ref, 1)); self.stub(x + 36, y, x + 44, y, pnet(ref, 2))
        self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/><rect x="%.1f" y="%.1f" width="20" height="18" fill="none" stroke="#8b949e" stroke-width="1.5"/>' % (x + 8, y - 12, x + 8, y + 12, x + 36, y - 12, x + 36, y + 12, x + 12, y - 9))
        self.text(x + 22, y - 18, ref, 8.5, '#8b949e', 'middle'); self.text(x + 22, y + 26, '32.768kHz', 9, '#c9d1d9', 'middle')
        self.pin(ref, 1, x, y); self.pin(ref, 2, x + 44, y)
        self.comp_els.append('</g>')

    def switch_h(self, ref, x, y):
        # left anchor = pins 3,4 (GND side); right anchor = pins 1,2 (raw side)
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — tact SPST</title>' % (ref, ref))
        self.comp_els.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#8b949e"/><circle cx="%.1f" cy="%.1f" r="2.6" fill="#8b949e"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2"/>' % (x, y, x + 60, y, x, y, x + 46, y - 16))
        self.text(x + 30, y - 24, ref.replace('SW_', 'SW '), 8.5, '#8b949e', 'middle')
        self.text(x - 4, y + 16, '3,4', 7.5, '#6e7681', 'end'); self.text(x + 64, y + 16, '1,2', 7.5, '#6e7681')
        self.pin(ref, 3, x, y); self.pin(ref, 4, x, y); self.pin(ref, 1, x + 60, y); self.pin(ref, 2, x + 60, y)
        self.comp_els.append('</g>')

    def npn(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title>' % (ref, ref, comps[ref]['model']))
        self.stub(x - 40, y, x, y, pnet(ref, 2))
        self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="2.5"/>' % (x, y - 18, x, y + 18))
        for x1, y1, x2, y2 in ((x, y - 8, x + 16, y - 24), (x + 16, y - 24, x + 16, y - 40), (x, y + 8, x + 16, y + 24), (x + 16, y + 24, x + 16, y + 40)):
            self.comp_els.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8b949e" stroke-width="1.5"/>' % (x1, y1, x2, y2))
        self.comp_els.append('<path d="M %.1f %.1f l -8 -1 l 4 6 Z" fill="#8b949e"/>' % (x + 16, y + 24))
        self.text(x - 34, y - 6, '2', 7.5, '#6e7681'); self.text(x + 20, y - 32, '3', 7.5, '#6e7681'); self.text(x + 20, y + 36, '1', 7.5, '#6e7681')
        self.text(x + 30, y - 8, ref, 9, '#8b949e'); self.text(x + 30, y + 6, comps[ref]['model'], 9, '#c9d1d9')
        self.pin(ref, 2, x - 40, y); self.pin(ref, 3, x + 16, y - 40); self.pin(ref, 1, x + 16, y + 40)
        self.comp_els.append('</g>')

    def connector(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title><rect x="%.1f" y="%.1f" width="60" height="80" rx="6" fill="#161b22" stroke="#30363d" stroke-width="1.5"/>' % (ref, ref, comps[ref]['value'], x, y))
        self.text(x + 30, y + 20, ref, 10, '#e6edf3', 'middle', 'bold')
        self.text(x + 30, y + 36, '9-12V', 8.5, '#8b949e', 'middle')
        self.stub(x + 60, y + 20, x + 84, y + 20, pnet(ref, 1)); self.text(x + 52, y + 24, '1 +', 8, '#6e7681', 'end')
        self.stub(x + 60, y + 60, x + 84, y + 60, pnet(ref, 2)); self.text(x + 52, y + 64, '2 -', 8, '#6e7681', 'end')
        self.pin(ref, 1, x + 84, y + 20); self.pin(ref, 2, x + 84, y + 60)
        self.comp_els.append('</g>')

    def reg7805(self, ref, x, y):
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title><rect x="%.1f" y="%.1f" width="140" height="80" rx="6" fill="#161b22" stroke="#30363d" stroke-width="1.5"/>' % (ref, ref, comps[ref]['model'], x, y))
        self.text(x + 70, y + 26, ref, 12, '#e6edf3', 'middle', 'bold')
        self.text(x + 70, y + 42, '7805', 10, '#8b949e', 'middle')
        self.text(x + 70, y + 58, 'IN=1 GND=2 OUT=3', 7.5, '#6e7681', 'middle')
        self.stub(x, y + 40, x - 24, y + 40, pnet(ref, 1)); self.pin(ref, 1, x - 24, y + 40); self.tag(pnet(ref, 1), x - 30, y + 40, 'end')
        self.stub(x + 140, y + 40, x + 164, y + 40, pnet(ref, 3)); self.pin(ref, 3, x + 164, y + 40)
        self.stub(x + 70, y + 80, x + 70, y + 104, pnet(ref, 2)); self.pin(ref, 2, x + 70, y + 104)
        self.comp_els.append('</g>')

    # ---- gates ----
    def gate_and(self, x, y, chip, gi, ins, outp, disabled=False):
        na, nb = pnet(chip, ins[0]), pnet(chip, ins[1]); no = pnet(chip, outp)
        col = '#6e7681' if disabled else '#8b949e'
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s%s — AND</title>' % (chip, chip, 'ABCD'[gi]))
        self.stub(x - 20, y - 12, x, y - 12, na); self.stub(x - 20, y + 12, x, y + 12, nb); self.stub(x + 42, y, x + 62, y, no)
        self.comp_els.append('<path d="M %.1f %.1f L %.1f %.1f A 22 22 0 0 1 %.1f %.1f L %.1f %.1f Z" fill="#161b22" stroke="%s" stroke-width="1.5"/>' % (x, y - 22, x + 20, y - 22, x + 20, y + 22, x, y + 22, col))
        self.text(x + 4, y - 8, str(ins[0]), 7, '#6e7681'); self.text(x + 4, y + 16, str(ins[1]), 7, '#6e7681'); self.text(x + 46, y - 6, str(outp), 7, '#6e7681')
        self.text(x - 34, y + 4, 'ABCD'[gi], 10, '#58a6ff', 'end', 'bold')
        self.pin(chip, ins[0], x - 20, y - 12); self.pin(chip, ins[1], x - 20, y + 12); self.pin(chip, outp, x + 62, y)
        self.tag(na, x - 26, y - 12, 'end'); self.tag(nb, x - 26, y + 12, 'end'); self.tag(no, x + 68, y, 'start')
        self.comp_els.append('</g>')

    def gate_or(self, x, y, chip, gi, ins, outp, disabled=False):
        na, nb = pnet(chip, ins[0]), pnet(chip, ins[1]); no = pnet(chip, outp)
        col = '#6e7681' if disabled else '#8b949e'
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s%s — OR</title>' % (chip, chip, 'ABCD'[gi]))
        self.stub(x - 20, y - 12, x + 7, y - 12, na); self.stub(x - 20, y + 12, x + 7, y + 12, nb); self.stub(x + 46, y, x + 66, y, no)
        self.comp_els.append('<path d="M %.1f %.1f Q %.1f %.1f %.1f %.1f Q %.1f %.1f %.1f %.1f Q %.1f %.1f %.1f %.1f Z" fill="#161b22" stroke="%s" stroke-width="1.5"/>' % (x, y - 22, x + 14, y, x, y + 22, x + 28, y + 22, x + 46, y, x + 28, y - 22, x, y - 22, col))
        self.text(x + 8, y - 8, str(ins[0]), 7, '#6e7681'); self.text(x + 8, y + 16, str(ins[1]), 7, '#6e7681'); self.text(x + 50, y - 6, str(outp), 7, '#6e7681')
        self.text(x - 34, y + 4, 'ABCD'[gi], 10, '#58a6ff', 'end', 'bold')
        self.pin(chip, ins[0], x - 20, y - 12); self.pin(chip, ins[1], x - 20, y + 12); self.pin(chip, outp, x + 66, y)
        self.tag(na, x - 26, y - 12, 'end'); self.tag(nb, x - 26, y + 12, 'end'); self.tag(no, x + 72, y, 'start')
        self.comp_els.append('</g>')

    def gate_inv(self, x, y, chip, ins, outp, label):
        # Schmitt NAND wired as inverter (inputs tied). Points right.
        ni = pnet(chip, ins[0]); no = pnet(chip, outp)
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — Schmitt inverter (%s)</title>' % (chip, label, comps[chip]['model']))
        self.stub(x - 20, y, x, y, ni); self.stub(x + 44, y, x + 60, y, no)
        self.comp_els.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="#161b22" stroke="#8b949e" stroke-width="1.5"/><circle cx="%.1f" cy="%.1f" r="4" fill="#161b22" stroke="#8b949e" stroke-width="1.5"/><path d="M %.1f %.1f h 7 v -8 h 7 v 8" fill="none" stroke="#8b949e" stroke-width="1.2"/>' % (x, y - 16, x, y + 16, x + 36, y, x + 40, y, x + 8, y + 4))
        self.text(x - 14, y - 8, ','.join(str(p) for p in ins), 7, '#6e7681', 'end'); self.text(x + 48, y - 8, str(outp), 7, '#6e7681')
        self.text(x + 20, y - 24, label, 9.5, '#58a6ff', 'middle', 'bold')
        for p in ins:
            self.pin(chip, p, x - 20, y)
        self.pin(chip, outp, x + 60, y)
        self.tag(ni, x - 26, y, 'end'); self.tag(no, x + 66, y, 'start')
        self.comp_els.append('</g>')

    def gate_chip(self, ref, kind, x, y):
        w, h = 540, 400
        model = comps[ref]['model']
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — %s</title><rect x="%.1f" y="%.1f" width="%d" height="%d" rx="10" fill="#121820" stroke="#3d4654" stroke-width="1.5" stroke-dasharray="6 4"/>' % (ref, ref, model, x, y, w, h))
        self.text(x + 20, y + 26, '%s — %s' % (ref, model), 13, '#e6edf3', 'start', 'bold')
        self.text(x + 20, y + 46, '\u0686\u0647\u0627\u0631 \u06af\u06cc\u062a ' + ('AND' if kind == 'and' else 'OR') + ' \u062f\u0648 \u0648\u0631\u0648\u062f\u06cc', 10, '#8b949e')
        # power pins 14 / 7
        self.stub(x + 380, y + 42, x + 394, y + 42, pnet(ref, 14)); self.pin(ref, 14, x + 394, y + 42); self.tag(pnet(ref, 14), x + 400, y + 42)
        self.text(x + 376, y + 46, '14', 7.5, '#6e7681', 'end')
        self.stub(x + 452, y + 42, x + 466, y + 42, pnet(ref, 7)); self.pin(ref, 7, x + 466, y + 42); self.tag(pnet(ref, 7), x + 472, y + 42)
        self.text(x + 448, y + 46, '7', 7.5, '#6e7681', 'end')
        pairs = [((1, 2), 3), ((5, 6), 4), ((8, 9), 10), ((12, 13), 11)]
        for gi, (ins, outp) in enumerate(pairs):
            gy = y + 90 + gi * 80
            disabled = (pnet(ref, outp) == 'NC')
            if kind == 'and':
                self.gate_and(x + 260, gy, ref, gi, ins, outp, disabled)
            else:
                self.gate_or(x + 260, gy, ref, gi, ins, outp, disabled)
            if disabled:
                self.text(x + 340, gy + 30, '\u0628\u0644\u0627\u0627\u0633\u062a\u0641\u0627\u062f\u0647 \u2014 \u0648\u0631\u0648\u062f\u06cc\u200c\u0647\u0627 GND', 8.5, '#6e7681')
        self.comp_els.append('</g>')

    # ---- CD4026 + resistor chain + display (one digit column) ----
    def digit_column(self, ref, dig, ds, x, y, header):
        w, h = 250, 170
        self.text(x + 125, y - 70, header, 12.5, '#e6edf3', 'middle', 'bold')
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — CD4026B (%s)</title><rect x="%.1f" y="%.1f" width="%d" height="%d" rx="6" fill="#161b22" stroke="#30363d" stroke-width="1.5"/>' % (ref, ref, dig, x, y, w, h))
        self.text(x + 125, y + 80, ref, 13, '#e6edf3', 'middle', 'bold')
        self.text(x + 125, y + 96, 'CD4026B', 10, '#8b949e', 'middle')
        self.text(x + 125, y + 112, dig + ' \u2192 ' + ds, 9.5, '#8b949e', 'middle')
        # top pins 1,2,3,15 (staggered tags)
        for i, p in enumerate((1, 2, 3, 15)):
            px = x + 40 + i * 60
            net = pnet(ref, p)
            self.stub(px, y, px, y - 26, net); self.pin(ref, p, px, y - 26)
            self.text(px, y + 12, str(p), 7.5, '#6e7681', 'middle')
            nm = {1: 'CLK', 2: 'INH', 3: 'DE IN', 15: 'RST'}[p]
            self.text(px, y + 24, nm, 7.5, '#8b949e', 'middle')
            self.tag(net, px, y - 36 if i % 2 == 0 else y - 52, 'middle')
        # left power 16,8 ; right 5,4,14
        for p, py in ((16, y + 50), (8, y + 120)):
            net = pnet(ref, p)
            self.stub(x, py, x - 24, py, net); self.pin(ref, p, x - 24, py)
            self.text(x + 7, py + 3, str(p), 7.5, '#6e7681'); self.text(x + 22, py + 3, 'VDD' if p == 16 else 'VSS', 8, '#8b949e')
            self.tag(net, x - 30, py, 'end')
        for p, py, nm in ((5, y + 50, 'CARRY'), (4, y + 85, 'DE OUT'), (14, y + 120, 'UC')):
            net = pnet(ref, p)
            self.stub(x + w, py, x + w + 24, py, net); self.pin(ref, p, x + w + 24, py)
            self.text(x + w - 7, py + 3, str(p), 7.5, '#6e7681', 'end'); self.text(x + w - 22, py + 3, nm, 8, '#8b949e', 'end')
            self.tag(net, x + w + 30, py, 'start')
        # bottom segment pins a..g
        segmap = [('a', 10), ('b', 12), ('c', 13), ('d', 9), ('e', 11), ('f', 6), ('g', 7)]
        segx = {}
        for i, (s, p) in enumerate(segmap):
            sx = x + 25 + i * (200 / 6)
            segx[s] = sx
            net = pnet(ref, p)
            self.stub(sx, y + h, sx, y + h + 26, net); self.pin(ref, p, sx, y + h + 26)
            self.text(sx, y + h - 20, s, 10, '#39c5cf', 'middle', 'bold'); self.text(sx, y + h - 8, str(p), 7, '#6e7681', 'middle')
        self.comp_els.append('</g>')
        # resistors + wires down
        ry = y + 240
        for s, p in segmap:
            sx = segx[s]
            rr = 'R_%s%s' % (dig, s.upper())
            segnet = pnet(ref, p)
            self.wire(segnet, [(sx, y + h + 26), (sx, ry)])
            self.res_v(rr, sx, ry)
        # display
        dy = y + 400
        self.display(ds, dig, x + 50, dy)
        # route resistor pin2 -> display segment pins
        dispin = {'a': 7, 'b': 6, 'c': 4, 'd': 2, 'e': 1, 'f': 9, 'g': 10}
        leftpins = {1: 0, 2: 1, 4: 3}   # display pin -> stub index (left side top->bottom 1,2,3,4,5)
        rightpins = {10: 0, 9: 1, 7: 3, 6: 4}
        for i, (s, p) in enumerate(segmap):
            sx = segx[s]
            dp = dispin[s]
            dspnet = pnet(ds, dp)
            chy = y + 315 + i * 9
            if dp in leftpins:
                sy = dy + 30 + leftpins[dp] * 34
                self.wire(dspnet, [(sx, ry + 60), (sx, chy), (x + 5, chy), (x + 5, sy), (x + 26, sy)])
            else:
                sy = dy + 30 + rightpins[dp] * 34
                self.wire(dspnet, [(sx, ry + 60), (sx, chy), (x + 235, chy), (x + 235, sy), (x + 224, sy)])

    def display(self, ref, dig, x, y):
        w, h = 150, 190
        self.comp_els.append('<g class="comp" data-ref="%s"><title>%s — SC52-11EWA CC</title><rect x="%.1f" y="%.1f" width="%d" height="%d" rx="10" fill="#0b0f14" stroke="#30363d" stroke-width="1.5"/>' % (ref, ref, x, y, w, h))
        # faint 8
        cx, cy = x + 75, y + 95
        def hseg(sx, sy):
            return '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#1b2129" stroke="#2d333b" stroke-width="0.8"/>' % (sx - 20, sy, sx - 14, sy - 5, sx + 14, sy - 5, sx + 20, sy, sx + 14, sy + 5, sx - 14, sy + 5)
        def vseg(sx, sy):
            return '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#1b2129" stroke="#2d333b" stroke-width="0.8"/>' % (sx, sy - 20, sx + 5, sy - 14, sx + 5, sy + 14, sx, sy + 20, sx - 5, sy + 14, sx - 5, sy - 14)
        self.comp_els.append(hseg(cx, cy - 62) + vseg(cx + 30, cy - 32) + vseg(cx + 30, cy + 32) + hseg(cx, cy + 62) + vseg(cx - 30, cy + 32) + vseg(cx - 30, cy - 32) + hseg(cx, cy))
        # left stubs: pins 1(e),2(d),3(COM),4(c),5(DP) ; right: 10(g),9(f),8(COM),7(a),6(b)
        for i, (p, nm) in enumerate(((1, 'e'), (2, 'd'), (3, 'COM'), (4, 'c'), (5, 'DP'))):
            py = y + 30 + i * 34
            net = pnet(ref, p)
            self.stub(x, py, x - 24, py, net); self.pin(ref, p, x - 24, py)
            self.text(x + 7, py + 3, str(p), 7.5, '#6e7681'); self.text(x + 22, py + 3, nm, 8, '#8b949e')
        for i, (p, nm) in enumerate(((10, 'g'), (9, 'f'), (8, 'COM'), (7, 'a'), (6, 'b'))):
            py = y + 30 + i * 34
            net = pnet(ref, p)
            self.stub(x + w, py, x + w + 24, py, net); self.pin(ref, p, x + w + 24, py)
            self.text(x + w - 7, py + 3, str(p), 7.5, '#6e7681', 'end'); self.text(x + w - 22, py + 3, nm, 8, '#8b949e', 'end')
        self.text(x + 75, y + 208, ref + ' \u2014 \u06a9\u0627\u062a\u062f \u0645\u0634\u062a\u0631\u06a9', 9.5, '#8b949e', 'middle')
        self.comp_els.append('</g>')
        # COM -> GND, DP -> NC (routed around)
        self.wire('GND', [(x - 24, y + 98), (x - 40, y + 98), (x - 40, y + 225)])
        self.tag('GND', x - 40, y + 238, 'middle')
        self.wire('GND', [(x + w + 24, y + 98), (x + 290, y + 98), (x + 290, y + 225)])
        self.tag('GND', x + 290, y + 238, 'middle')
        self.tag('NC', x - 30, y + 166, 'end')

S = Sch()
for r in REGIONS:
    S.region(r)

# ================= POWER =================
S.connector('J1', 70, 130)
S.wire('VIN', [(154, 150), (180, 150)])
S.diode_h('D1', 180, 150)
S.wire('VIN2', [(222, 150), (436, 150)], dots=[(300, 150), (380, 150)])
S.cap_v('C_IN1', 300, 150); S.cap_v('C_IN2', 380, 150)
S.reg7805('U16', 460, 110)
S.wire('VCC', [(624, 150), (740, 150)], dots=[(650, 150), (710, 150)])
S.tag('VCC', 746, 150)
S.cap_v('C_OUT1', 650, 150); S.cap_v('C_OUT2', 710, 150)
# GND rail
S.wire('GND', [(154, 190), (154, 260), (740, 260)], dots=[(300, 260), (380, 260), (530, 260), (650, 260), (710, 260)])
S.tag('GND', 746, 260)
for cx in (300, 380, 650, 710):
    S.wire('GND', [(cx, 194), (cx, 260)])
S.wire('GND', [(530, 214), (530, 260)])
# C_BULK
S.wire('VCC', [(740, 150), (740, 300), (660, 300)])
S.cap_v('C_BULK', 660, 300, pol=True)
S.wire('GND', [(660, 344), (660, 380), (740, 380)])
S.tag('GND', 746, 380)
# bypass row
S.wire('VCC', [(80, 420), (740, 420)], dots=[(100 + i * 44, 420) for i in range(15)])
S.wire('GND', [(80, 480), (740, 480)], dots=[(100 + i * 44, 480) for i in range(15)])
S.tag('VCC', 76, 420, 'end'); S.tag('GND', 76, 480, 'end')
for i in range(15):
    bx = 100 + i * 44
    S.cap_v('C_BYP%d' % (i + 1), bx, 420)
    S.text(bx, 412, str(i + 1), 7, '#6e7681', 'middle')
S.text(80, 510, 'C_BYP1\u2026C_BYP15 = 100nF \u2014 \u0686\u0633\u0628\u06cc\u062f\u0647 \u0628\u0647 VDD/VSS \u0647\u0631 \u06cc\u06a9 \u0627\u0632 U1\u2026U15', 10, '#8b949e')

# ================= TIMEBASE =================
S.dip('U2', 1000, 170, 220, [1, 2, 3, 4, 5, 6, 7], [14, 13, 12, 11, 10, 9, 8], wired={2, 5})
S.wire('FF1_D', [(976, 246), (860, 246), (860, 354), (976, 354)])
S.dip('U1', 1420, 170, 220, [1, 2, 3, 4, 5, 6, 7, 8], [16, 15, 14, 13, 12, 11, 10, 9], wired={10, 11})
# crystal network (Fig.13 CD4060)
S.wire('XTAL_A', [(1664, 390), (1780, 390)], dots=[(1740, 390)])
S.xtal_h('Y1', 1780, 390)
S.wire('XTAL_B', [(1824, 390), (1940, 390)], dots=[(1900, 390)])
S.res_h('R_S', 1940, 390)
S.wire('OSC_FB', [(2020, 390), (2040, 390), (2040, 426), (1664, 426)])
S.wire('XTAL_A', [(1740, 390), (1740, 320), (1780, 320)])
S.res_h('R_C', 1780, 320)
S.wire('XTAL_B', [(1860, 320), (1900, 320), (1900, 390)])
S.cap_v('C1', 1740, 390); S.cap_v('C2', 1900, 390)
S.wire('GND', [(1740, 434), (1740, 460)]); S.tag('GND', 1740, 474, 'middle')
S.wire('GND', [(1900, 434), (1900, 460)]); S.tag('GND', 1900, 474, 'middle')
S.gate_inv(1480, 560, 'U15', (12, 13), 11, 'U15D')
S.text(840, 620, 'CLK1HZ: \u0627\u0648\u0644\u06cc\u0646 \u0644\u0628\u0647 \u0628\u0627\u0644\u0627\u0631\u0648\u0646\u062f\u0647 \u062f\u0642\u06cc\u0642\u0627\u064b 1.000s \u067e\u0633 \u0627\u0632 \u0631\u0641\u0639 \u0631\u06cc\u0633\u062a\u060c \u0633\u067e\u0633 1Hz \u062f\u0642\u06cc\u0642', 11, '#8b949e')
S.text(840, 642, 'U15D = \u06cc\u06a9 \u0686\u0647\u0627\u0631\u0645 CD4093B\u061b \u0648\u0631\u0648\u062f\u06cc\u200c\u0647\u0627\u06cc 12\u064c13 \u0628\u0647\u200c\u0647\u0645\u060c \u062e\u0631\u0648\u062c\u06cc 11\u061b FF1: D=Q\u0304 (U2.2\u2192U2.5)', 11, '#8b949e')

# ================= POR =================
S.res_v('R_POR', 120, 700); S.tag('VCC', 120, 680, 'middle')
S.cap_v('C_POR', 120, 800, pol=True)
S.wire('GND', [(120, 844), (120, 862)]); S.tag('GND', 120, 876, 'middle')
S.diode_v_up('D2', 230, 700); S.tag('VCC', 230, 680, 'middle')
S.wire('POR_N', [(120, 760), (120, 800)], dots=[(120, 780)])
S.wire('POR_N', [(230, 742), (230, 780), (120, 780)])
S.wire('POR_N', [(120, 780), (380, 780)])
S.gate_inv(400, 780, 'U15', (8, 9), 10, 'U15C')
S.text(60, 940, 'RST_GLOBAL = POR_RST OR BTN_MSTRST \u062a\u0648\u0633\u0637 U13A (1,2\u21923)\u061b \u067e\u0647\u0646\u0627\u06cc \u067e\u0627\u0644\u0633 POR \u2248 0.87s', 10.5, '#8b949e')
S.text(60, 962, 'D2: \u062a\u062e\u0644\u06cc\u0647 C_POR \u0647\u0646\u06af\u0627\u0645 \u062e\u0627\u0645\u0648\u0634\u200c\u0634\u062f\u0646 (\u0622\u0646\u062f=POR_N\u060c \u06a9\u0627\u062a\u062f=VCC)', 10.5, '#8b949e')

# ================= BUTTONS =================
btn_rows = [
    ('SET', 'U14', (1, 2), 3, 'A', 'SET \u2014 \u0648\u0631\u0648\u062f/\u062e\u0631\u0648\u062c \u062d\u0627\u0644\u062a \u062a\u0646\u0638\u06cc\u0645'),
    ('HOUR', 'U14', (5, 6), 4, 'B', 'HOUR+ \u2014 \u0627\u0641\u0632\u0627\u06cc\u0634 \u0633\u0627\u0639\u062a'),
    ('MIN', 'U14', (8, 9), 10, 'C', 'MIN+ \u2014 \u0627\u0641\u0632\u0627\u06cc\u0634 \u062f\u0642\u06cc\u0642\u0647'),
    ('SECRST', 'U14', (12, 13), 11, 'D', 'SEC RESET \u2014 \u062b\u0627\u0646\u06cc\u0647\u200c\u0635\u0641\u0631'),
    ('MSTRST', 'U15', (1, 2), 3, 'A', 'MASTER RESET \u2014 \u0631\u06cc\u0633\u062a \u06a9\u0644'),
]
for i, (name, chip, ins, outp, gl, title) in enumerate(btn_rows):
    y = 1130 + i * 180
    raw = 'BTN_%s_n' % name
    S.text(60, y - 46, title, 11.5, '#c9d1d9')
    S.switch_h('SW_' + name, 90, y)
    S.tag('GND', 84, y, 'end')
    S.wire(raw, [(150, y), (410, y)], dots=[(250, y), (330, y)])
    S.res_v('R_PU_' + name, 250, y - 60); S.tag('VCC', 250, y - 80, 'middle')
    S.cap_v('C_BTN_' + name, 330, y)
    S.wire('GND', [(330, y + 44), (330, y + 62)]); S.tag('GND', 330, y + 76, 'middle')
    S.gate_inv(430, y, chip, ins, outp, chip + gl)
S.text(60, 1920, 'BTN_MSTRST \u2192 U13A (OR \u0628\u0627 POR_RST) \u2192 RST_GLOBAL', 10.5, '#8b949e')
S.gate_inv(430, 2010, 'U15', (5, 6), 4, 'U15B')
S.text(60, 1980, 'U15B \u2014 \u0645\u0639\u06a9\u0648\u0633\u200c\u06a9\u0631\u062f\u0646 SET_MODE', 11.5, '#c9d1d9')
S.text(60, 2055, 'nSET_MODE \u2192 U11B: CLK_SEC = CLK1HZ AND nSET_MODE (\u062f\u0631 \u062d\u0627\u0644\u062a \u062a\u0646\u0638\u06cc\u0645 \u062b\u0627\u0646\u06cc\u0647 \u0645\u062a\u0648\u0642\u0641)', 10.5, '#8b949e')

# ================= GATES =================
S.gate_chip('U9', 'and', 860, 730)
S.gate_chip('U10', 'and', 1420, 730)
S.gate_chip('U11', 'and', 1980, 730)
S.gate_chip('U12', 'or', 860, 1170)
S.gate_chip('U13', 'or', 1420, 1170)
# inventory panel
ix, iy = 1980, 1170
S.bg.append('<rect x="%d" y="%d" width="540" height="400" rx="10" fill="#121820" stroke="#3d4654" stroke-width="1.5"/>' % (ix, iy))
S.text(ix + 20, iy + 28, '\u0641\u0647\u0631\u0633\u062a \u0642\u0637\u0639\u0627\u062a \u0641\u0639\u0627\u0644', 13, '#e6edf3', 'start', 'bold')
inv_lines = [
    'U1  CD4060B \u2014 \u067e\u0627\u06cc\u0647 \u0632\u0645\u0627\u0646 (DIP-16)',
    'U2  CD4013B \u2014 \u062f\u0648 \u0641\u0644\u06cc\u067e\u200c\u0641\u0644\u0627\u067e D (DIP-14)',
    'U3\u2026U8  CD4026B \u00d76 \u2014 \u0634\u0645\u0627\u0631\u0646\u062f\u0647/\u062f\u0631\u0627\u06cc\u0648\u0631 (DIP-16)',
    'U9\u2026U11  CD4081B \u00d73 \u2014 \u0686\u0647\u0627\u0631 AND (DIP-14)',
    'U12\u2026U13  CD4071B \u00d72 \u2014 \u0686\u0647\u0627\u0631 OR (DIP-14)',
    'U14  CD4093B \u2014 \u062f\u06cc\u0628\u0627\u0646\u0633 \u0686\u0647\u0627\u0631 \u06a9\u0644\u06cc\u062f (\u0645\u0646\u0637\u0642\u0647 \u062f\u06a9\u0645\u0647\u200c\u0647\u0627)',
    'U15  CD4093B \u2014 A:\u0631\u06cc\u0633\u062a \u06a9\u0644  B:nSET_MODE  C:POR  D:\u06a9\u0644\u0627\u06a9',
    'U16  7805 \u2014 \u0631\u06af\u0648\u0644\u0627\u062a\u0648\u0631 5V (TO-220)',
    'Q1  2N3904 \u2014 \u062f\u0631\u0627\u06cc\u0648\u0631 \u06a9\u0648\u0644\u0646 (TO-92)',
    'DS1\u2026DS6  SC52-11EWA \u00d76 \u2014 \u06a9\u0627\u062a\u062f \u0645\u0634\u062a\u0631\u06a9',
]
for i, ln in enumerate(inv_lines):
    S.text(ix + 20, iy + 56 + i * 22, ln, 10.5, '#c9d1d9')
pas_lines = [
    '\u0645\u0642\u0627\u0648\u0645\u062a\u200c\u0647\u0627: 42\u00d7470R \u0633\u06af\u0645\u0646\u062a \u00b7 6\u00d7100k \u0628\u0627\u0644\u0627\u06a9\u0634 \u00b7 10M \u00b7 220k \u00b7 10k \u00b7 2\u00d71k',
    '\u062e\u0627\u0632\u0646\u200c\u0647\u0627: 2\u00d718pF \u06a9\u0631\u06cc\u0633\u062a\u0627\u0644 \u00b7 5\u00d71uF \u062f\u06cc\u0628\u0627\u0646\u0633 \u00b7 10uF POR \u00b7 15\u00d7100nF \u0628\u0627\u06cc\u200c\u067e\u0633',
    '\u0631\u06af\u0648\u0644\u0627\u062a\u0648\u0631: 0.33uF + 100uF \u0648\u0631\u0648\u062f\u06cc \u00b7 100nF + 100uF \u062e\u0631\u0648\u062c\u06cc \u00b7 470uF \u0630\u062e\u06cc\u0631\u0647',
    '\u0633\u0627\u06cc\u0631: 5\u00d7 \u06a9\u0644\u06cc\u062f tact \u00b7 \u06a9\u0631\u06cc\u0633\u062a\u0627\u0644 32.768kHz \u00b7 2\u00d7LED \u00b7 D1/D2 \u00b7 J1',
]
for i, ln in enumerate(pas_lines):
    S.text(ix + 20, iy + 292 + i * 22, ln, 9.5, '#8b949e')

# ---- power pins of distributed Schmitt chips U14 / U15 ----
for ref, px in (('U14', 880), ('U15', 1240)):
    py = 1615
    S.text(px, py, ref + ' \u2014 CD4093B (\u062a\u063a\u0630\u06cc\u0647)', 10.5, '#8b949e')
    S.stub(px + 150, py - 4, px + 164, py - 4, pnet(ref, 14)); S.pin(ref, 14, px + 164, py - 4)
    S.text(px + 146, py, '14', 7.5, '#6e7681', 'end'); S.tag(pnet(ref, 14), px + 170, py - 4)
    S.stub(px + 240, py - 4, px + 254, py - 4, pnet(ref, 7)); S.pin(ref, 7, px + 254, py - 4)
    S.text(px + 236, py, '7', 7.5, '#6e7681', 'end'); S.tag(pnet(ref, 7), px + 260, py - 4)

# ================= COLON =================
S.tag('CLK1HZ', 954, 1950, 'end')
S.res_h('R_CB', 960, 1950)
S.wire('COLON_B', [(1040, 1950), (1100, 1950)])
S.npn('Q1', 1140, 1950)
S.wire('GND', [(1156, 1990), (1156, 2030)]); S.tag('GND', 1156, 2044, 'middle')
for x, rr, ll in ((1300, 'R_CL1', 'LED1'), (1450, 'R_CL2', 'LED2')):
    S.tag('VCC', x, 1740, 'middle')
    S.wire('VCC', [(x, 1750), (x, 1760)])
    S.res_v(rr, x, 1760)
    an = 'COLON_A1' if x == 1300 else 'COLON_A2'
    S.wire(an, [(x, 1820), (x, 1840)])
    S.led_v_down(ll, x, 1840)
S.wire('COLON_K', [(1450, 1882), (1450, 1900), (1156, 1900), (1156, 1910)], dots=[(1300, 1900)])
S.wire('COLON_K', [(1300, 1882), (1300, 1900)])
S.text(860, 2070, 'CLK1HZ \u2192 R_CB \u2192 \u0628\u06cc\u0633 Q1\u061b \u06a9\u0648\u0644\u0646 \u0628\u0627 1Hz \u0686\u0634\u0645\u06a9 \u0645\u06cc\u200c\u0632\u0646\u062f\u061b \u062c\u0631\u06cc\u0627\u0646 \u0647\u0631 LED \u2248 2.8mA', 11, '#8b949e')

# ================= COUNTERS + DISPLAYS =================
digits = [
    ('U8', 'HT', 'DS1', '\u062f\u0647\u06af\u0627\u0646 \u0633\u0627\u0639\u062a'),
    ('U7', 'HU', 'DS2', '\u06cc\u06a9\u0627\u0646 \u0633\u0627\u0639\u062a'),
    ('U6', 'MT', 'DS3', '\u062f\u0647\u06af\u0627\u0646 \u062f\u0642\u06cc\u0642\u0647'),
    ('U5', 'MU', 'DS4', '\u06cc\u06a9\u0627\u0646 \u062f\u0642\u06cc\u0642\u0647'),
    ('U4', 'ST', 'DS5', '\u062f\u0647\u06af\u0627\u0646 \u062b\u0627\u0646\u06cc\u0647'),
    ('U3', 'SU', 'DS6', '\u06cc\u06a9\u0627\u0646 \u062b\u0627\u0646\u06cc\u0647'),
]
for i, (ref, dig, ds, hdr) in enumerate(digits):
    S.digit_column(ref, dig, ds, 60 + i * 420, 2260, hdr + ' (' + dig + ')')

# footer
n_pins = len(S.pins)
n_refs = len(comps)
S.text(40, 2975, '\u062a\u0648\u0644\u06cc\u062f \u062e\u0648\u062f\u06a9\u0627\u0631 \u0627\u0632 netlist.csv \u2014 %d \u067e\u06cc\u0646\u060c %d \u0646\u062a\u060c %d \u0642\u0637\u0639\u0647\u061b \u0647\u0631 \u067e\u06cc\u0646 \u062f\u0642\u06cc\u0642\u0627\u064b \u06cc\u06a9\u200c\u0628\u0627\u0631 \u0631\u0633\u0645 \u0634\u062f\u0647 \u0627\u0633\u062a.' % (n_pins, len(netdesc), n_refs), 12, '#8b949e')
S.text(40, 3000, '\u0628\u0631\u0686\u0633\u0628\u200c\u0647\u0627\u06cc \u0647\u0645\u200c\u0646\u0627\u0645 = \u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u06a9\u062a\u0631\u06cc\u06a9\u06cc (\u06a9\u0644\u06cc\u06a9 \u06a9\u0646\u06cc\u062f \u062a\u0627 \u0645\u0633\u06cc\u0631 \u0646\u062a \u0631\u0648\u06cc \u06a9\u0644 \u0646\u0642\u0634\u0647 \u0631\u062f\u06cc\u0627\u0628\u06cc \u0634\u0648\u062f)\u061b \u062a\u0642\u0627\u0637\u0639 \u0628\u062f\u0648\u0646 \u0646\u0642\u0637\u0647 = \u0628\u062f\u0648\u0646 \u0627\u062a\u0635\u0627\u0644\u061b \u0646\u0642\u0637\u0647 = \u06af\u0631\u0647 \u0647\u0645\u200c\u0646\u062a.', 11, '#6e7681')
S.text(40, 3022, '\u062a\u0623\u06cc\u06cc\u062f \u0646\u0647\u0627\u06cc\u06cc \u0633\u062e\u062a\u200c\u0627\u0641\u0632\u0627\u0631 \u0646\u06cc\u0627\u0632\u0645\u0646\u062f \u0646\u0645\u0648\u0646\u0647\u200c\u0633\u0627\u0632\u06cc \u0648 \u062a\u0633\u062a \u0631\u0648\u06cc \u0628\u0631\u062f \u0627\u0633\u062a\u061b \u0627\u06cc\u0646 \u0646\u0642\u0634\u0647 \u0627\u0632 \u0646\u062a\u200c\u0644\u06cc\u0633\u062a \u062a\u0623\u06cc\u06cc\u062f\u0634\u062f\u0647 \u0631\u0641\u062a\u0627\u0631\u06cc \u062a\u0648\u0644\u06cc\u062f \u0634\u062f\u0647.', 11, '#6e7681')

# ---------------- coverage assertion ----------------
csv_pins = set()
with open(NETLIST, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        csv_pins.add((r['Ref'], r['Pin']))
missing = csv_pins - S.drawn
extra = S.drawn - csv_pins
assert not missing, 'MISSING PINS: %s' % sorted(missing)
assert not extra, 'EXTRA PINS: %s' % sorted(extra)

# ---------------- assemble SVG ----------------
svg = []
svg.append('<svg id="schsvg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet" font-family="Segoe UI, Tahoma, sans-serif">' % (SHEET_W, SHEET_H))
svg.append('<defs><filter id="schglow" x="-50%%" y="-50%%" width="200%%" height="200%%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'.replace('%%', '%'))
svg.append('<rect x="0" y="0" width="%d" height="%d" fill="#0d1117"/>' % (SHEET_W, SHEET_H))
svg.extend(S.bg)
svg.append('<g id="wirelayer">'); svg.extend(S.wire_els); svg.append('</g>')
svg.append('<g id="complayer">'); svg.extend(S.comp_els); svg.append('</g>')
svg.append('<g id="taglayer">'); svg.extend(S.tag_els); svg.append('</g>')
svg.append('<g id="tracelayer"></g>')
svg.append('</svg>')
SVG = '\n'.join(svg)

PINS_JSON = json.dumps(S.pins, ensure_ascii=False)
TAGS_JSON = json.dumps(S.tags, ensure_ascii=False)
WIRES_JSON = json.dumps(S.wires, ensure_ascii=False)
COMP_JSON = json.dumps({k: {'model': v['model'], 'value': v['value'], 'pkg': v['pkg'], 'pins': v['pins']} for k, v in comps.items()}, ensure_ascii=False)
NETDESC_JSON = json.dumps(netdesc, ensure_ascii=False)
NETCOL_JSON = json.dumps({n: net_color(n) for n in list(netdesc) + ['NC']}, ensure_ascii=False)
REG_JSON = json.dumps(REGIONS, ensure_ascii=False)

# ---------------- HTML template ----------------
TEMPLATE = r'''<style>
.clksch{--bg:#0d1117;--panel:#161b22;--border:#30363d;--txt:#c9d1d9;--dim:#8b949e;--acc:#58a6ff;
  background:var(--bg);color:var(--txt);font-family:"Segoe UI",Tahoma,sans-serif;border:1px solid var(--border);
  border-radius:10px;display:flex;flex-direction:column;height:720px;overflow:hidden;direction:rtl}
.clksch *{box-sizing:border-box}
.clksch .toolbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border);background:var(--panel)}
.clksch .toolbar .ttl{font-weight:700;color:#e6edf3;font-size:14px;margin-left:8px}
.clksch button,.clksch select,.clksch input{background:#21262d;color:var(--txt);border:1px solid var(--border);border-radius:6px;
  padding:5px 10px;font-size:12px;font-family:inherit;cursor:pointer}
.clksch button:hover{border-color:var(--acc);color:var(--acc)}
.clksch input{cursor:text;width:170px;direction:ltr;text-align:left;font-family:Consolas,monospace}
.clksch .main{flex:1;display:flex;min-height:0}
.clksch .svgwrap{flex:1;min-width:0;position:relative;background:var(--bg)}
.clksch svg{width:100%;height:100%;display:block;touch-action:none;cursor:grab}
.clksch svg:active{cursor:grabbing}
.clksch .panel{width:280px;border-right:1px solid var(--border);background:var(--panel);overflow-y:auto;padding:10px;font-size:12px}
.clksch .panel h3{margin:0 0 6px;font-size:13px;color:#e6edf3}
.clksch .panel .desc{color:var(--dim);font-size:11.5px;line-height:1.6;margin-bottom:8px}
.clksch .nethead{display:flex;align-items:center;gap:6px;direction:ltr;justify-content:flex-end}
.clksch .dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.clksch .netname{font-family:Consolas,monospace;font-weight:700;font-size:13px}
.clksch .conn{display:flex;justify-content:space-between;gap:6px;padding:3px 6px;border-radius:4px;cursor:pointer;direction:ltr;font-family:Consolas,monospace;font-size:11px}
.clksch .conn:hover{background:#21262d}
.clksch .conn .pn{color:var(--dim)}
.clksch .pintable{width:100%;border-collapse:collapse;direction:ltr;font-family:Consolas,monospace;font-size:10.5px}
.clksch .pintable td{padding:2px 5px;border-bottom:1px solid #21262d}
.clksch .legend{display:flex;flex-wrap:wrap;gap:8px;padding:6px 10px;border-top:1px solid var(--border);background:var(--panel);font-size:11px;color:var(--dim)}
.clksch .lg{display:flex;align-items:center;gap:4px}
.clksch .stub{cursor:pointer}
.clksch .tag{cursor:pointer}
.clksch .comp{cursor:pointer}
.clksch .w{transition:opacity .15s}
.clksch svg.tracing .w:not(.sel){opacity:.14}
.clksch svg.tracing .tag:not(.sel){opacity:.3}
.clksch svg.tracing .stub:not(.sel){opacity:.3}
.clksch .sel{filter:url(#schglow)}
.clksch polyline.sel{stroke-width:3.5}
.clksch line.sel{stroke-width:3.5}
.clksch g.tag.sel rect{stroke-width:2}
.clksch .trace{fill:none;stroke-width:3;opacity:.85;stroke-dasharray:12 7;animation:clkschdash 1.1s linear infinite;pointer-events:none}
@keyframes clkschdash{to{stroke-dashoffset:-38}}
.clksch .hint{color:var(--dim);font-size:11px;line-height:1.7}
</style>
<div class="clksch">
  <div class="toolbar">
    <span class="ttl">نقشه کامل مدار ساعت دیجیتال</span>
    <button id="sch-zin" title="بزرگ‌نمایی">+</button>
    <button id="sch-zout" title="کوچک‌نمایی">−</button>
    <button id="sch-fit">کل نقشه</button>
    <select id="sch-region"></select>
    <input id="sch-search" placeholder="جستجوی نت یا قطعه… مثلاً CLK1HZ یا U3">
    <button id="sch-go">جستجو</button>
    <button id="sch-clear">پاک‌کردن انتخاب</button>
  </div>
  <div class="main">
    <div class="svgwrap">__SVG__</div>
    <div class="panel" id="sch-panel"></div>
  </div>
  <div class="legend">
    <span class="lg"><span class="dot" style="background:#ff6b6b"></span>VCC</span>
    <span class="lg"><span class="dot" style="background:#9aa4b2"></span>GND</span>
    <span class="lg"><span class="dot" style="background:#d2a8ff"></span>اسیلاتور</span>
    <span class="lg"><span class="dot" style="background:#79c0ff"></span>کلاک</span>
    <span class="lg"><span class="dot" style="background:#f0883e"></span>ریست/دیکود</span>
    <span class="lg"><span class="dot" style="background:#7ee787"></span>کری</span>
    <span class="lg"><span class="dot" style="background:#f778ba"></span>دکمه/حالت</span>
    <span class="lg"><span class="dot" style="background:#39c5cf"></span>سگمنت</span>
    <span class="lg"><span class="dot" style="background:#e3b341"></span>کولن</span>
  </div>
</div>
<script>
(function(){
const PINS=__PINS__;
const TAGS=__TAGS__;
const WIRES=__WIRES__;
const COMP=__COMP__;
const NET_DESC=__NETDESC__;
const NET_COL=__NETCOL__;
const REGIONS=__REGIONS__;
const SHEET_W=__SW__, SHEET_H=__SH__;
const svg=document.getElementById('schsvg');
const panel=document.getElementById('sch-panel');
const NS='http://www.w3.org/2000/svg';
let vb={x:0,y:0,w:SHEET_W,h:SHEET_H};
function applyVB(){svg.setAttribute('viewBox',vb.x+' '+vb.y+' '+vb.w+' '+vb.h);}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function col(n){return NET_COL[n]||'#6e7681';}
function clearSel(){
  svg.classList.remove('tracing');
  svg.querySelectorAll('.sel').forEach(e=>e.classList.remove('sel'));
  document.getElementById('tracelayer').innerHTML='';
}
function defaultPanel(){
  panel.innerHTML='<h3>راهنما</h3><div class="hint">روی هر برچسب نت یا پین کلیک کنید تا همان نت در کل نقشه هایلایت و مسیرش ردیابی شود.<br>روی بدنه قطعه کلیک کنید تا جدول پین‌هایش نمایش داده شود.<br>با چرخ ماوس زوم و با درگ جابه‌جا شوید.<br><br>برچسب‌های هم‌نام = اتصال الکتریکی.<br>تقاطع بدون نقطه = بدون اتصال؛ نقطه = گره هم‌نت.</div>'
  +'<h3 style="margin-top:10px">آمار</h3><div class="desc">'+PINS.length+' پین · '+Object.keys(NET_DESC).length+' نت · '+Object.keys(COMP).length+' قطعه</div>';
}
function centerOn(x,y,w){
  w=w||900;const h=w*SHEET_H/SHEET_W;
  vb={x:x-w/2,y:y-h/2,w:w,h:h};applyVB();
}
function selectNet(net){
  clearSel();
  svg.classList.add('tracing');
  svg.querySelectorAll('[data-net="'+net+'"]').forEach(e=>e.classList.add('sel'));
  const pts=[];
  PINS.forEach(p=>{if(p.net===net)pts.push([p.x,p.y]);});
  TAGS.forEach(t=>{if(t.net===net)pts.push([t.x,t.y]);});
  const uniq=[];pts.forEach(p=>{if(!uniq.some(q=>Math.hypot(q[0]-p[0],q[1]-p[1])<12))uniq.push(p);});
  uniq.sort((a,b)=>a[1]-b[1]||a[0]-b[0]);
  let traced=false;
  if(uniq.length>1&&uniq.length<=14){
    let d='M'+uniq[0][0]+' '+uniq[0][1];
    for(let i=1;i<uniq.length;i++){const x0=uniq[i-1][0],y0=uniq[i-1][1],x1=uniq[i][0],y1=uniq[i][1],mx=(x0+x1)/2;
      d+=' C '+mx+' '+y0+', '+mx+' '+y1+', '+x1+' '+y1;}
    const path=document.createElementNS(NS,'path');
    path.setAttribute('d',d);path.setAttribute('class','trace');path.setAttribute('stroke',col(net));
    document.getElementById('tracelayer').appendChild(path);traced=true;
  }
  const conns=PINS.filter(p=>p.net===net).sort((a,b)=>a.ref.localeCompare(b.ref,undefined,{numeric:true})||(+a.pin)-(+b.pin));
  let h='<div class="nethead"><span class="netname" style="color:'+col(net)+'">'+esc(net)+'</span><span class="dot" style="background:'+col(net)+'"></span></div>';
  h+='<div class="desc">'+esc(NET_DESC[net]||'')+'<br>'+conns.length+' پین متصل'+(traced?' · مسیر ردیابی شد':' · شبکه پرتعداد — همه پین‌ها هایلایت شد')+'</div>';
  h+='<h3>اتصالات</h3>';
  conns.forEach(p=>{h+='<div class="conn" data-x="'+p.x+'" data-y="'+p.y+'"><span>'+esc(p.ref)+' · pin '+esc(p.pin)+'</span><span class="pn">'+esc(p.name)+'</span></div>';});
  panel.innerHTML=h;
  panel.querySelectorAll('.conn').forEach(el=>el.addEventListener('click',()=>centerOn(+el.dataset.x,+el.dataset.y,700)));
}
function selectComp(ref){
  clearSel();
  const c=COMP[ref];if(!c)return;
  svg.querySelectorAll('[data-ref="'+ref+'"]').forEach(e=>e.classList.add('sel'));
  let h='<div class="nethead"><span class="netname">'+esc(ref)+'</span></div>';
  h+='<div class="desc">'+esc(c.model)+' · '+esc(c.value)+' · '+esc(c.pkg)+'</div><h3>پین‌ها</h3>';
  h+='<table class="pintable"><tr><td>پین</td><td>نام</td><td>نت</td></tr>';
  Object.keys(c.pins).sort((a,b)=>(+a)-(+b)).forEach(p=>{
    const nm=c.pins[p][0],net=c.pins[p][1];
    h+='<tr><td>'+esc(p)+'</td><td>'+esc(nm)+'</td><td style="color:'+col(net)+';cursor:pointer" data-net-jump="'+esc(net)+'">'+esc(net)+'</td></tr>';
  });
  h+='</table>';
  panel.innerHTML=h;
  panel.querySelectorAll('[data-net-jump]').forEach(el=>el.addEventListener('click',()=>selectNet(el.dataset.netJump)));
  const ps=PINS.filter(p=>p.ref===ref);
  if(ps.length){const mx=ps.reduce((s,p)=>s+p.x,0)/ps.length,my=ps.reduce((s,p)=>s+p.y,0)/ps.length;centerOn(mx,my,800);}
}
svg.addEventListener('click',e=>{
  const t=e.target.closest('[data-net]');
  if(t){selectNet(t.getAttribute('data-net'));return;}
  const c=e.target.closest('[data-ref]');
  if(c){selectComp(c.getAttribute('data-ref'));return;}
  clearSel();defaultPanel();
});
// pan + zoom
let drag=null;
svg.addEventListener('pointerdown',e=>{
  if(e.target.closest('[data-net],[data-ref]'))return;
  drag={x:e.clientX,y:e.clientY,vx:vb.x,vy:vb.y};svg.setPointerCapture(e.pointerId);
});
svg.addEventListener('pointermove',e=>{
  if(!drag)return;const r=svg.getBoundingClientRect();const k=vb.w/r.width;
  vb.x=drag.vx-(e.clientX-drag.x)*k;vb.y=drag.vy-(e.clientY-drag.y)*k;applyVB();
});
svg.addEventListener('pointerup',()=>drag=null);
svg.addEventListener('pointercancel',()=>drag=null);
svg.addEventListener('wheel',e=>{
  e.preventDefault();
  const r=svg.getBoundingClientRect();
  const px=vb.x+(e.clientX-r.left)/r.width*vb.w;
  const py=vb.y+(e.clientY-r.top)/r.height*vb.h;
  const f=e.deltaY>0?1.15:1/1.15;
  const nw=Math.min(8000,Math.max(250,vb.w*f));const k=nw/vb.w;
  vb.x=px-(px-vb.x)*k;vb.y=py-(py-vb.y)*k;vb.w=nw;vb.h*=k;applyVB();
},{passive:false});
function zoomBy(f){
  const cx=vb.x+vb.w/2,cy=vb.y+vb.h/2;
  const nw=Math.min(8000,Math.max(250,vb.w*f));const k=nw/vb.w;
  vb.w=nw;vb.h*=k;vb.x=cx-vb.w/2;vb.y=cy-vb.h/2;applyVB();
}
document.getElementById('sch-zin').addEventListener('click',()=>zoomBy(1/1.3));
document.getElementById('sch-zout').addEventListener('click',()=>zoomBy(1.3));
document.getElementById('sch-fit').addEventListener('click',()=>{vb={x:0,y:0,w:SHEET_W,h:SHEET_H};applyVB();});
document.getElementById('sch-clear').addEventListener('click',()=>{clearSel();defaultPanel();});
const rsel=document.getElementById('sch-region');
REGIONS.forEach(r=>{const o=document.createElement('option');o.value=r.id;o.textContent=r.title;rsel.appendChild(o);});
rsel.addEventListener('change',()=>{
  const r=REGIONS.find(q=>q.id===rsel.value);if(!r)return;
  const pad=30;vb={x:r.x-pad,y:r.y-pad,w:r.w+2*pad,h:r.h+2*pad};applyVB();
});
function doSearch(){
  const q=document.getElementById('sch-search').value.trim().toUpperCase();if(!q)return;
  let net=Object.keys(NET_DESC).find(n=>n===q)||Object.keys(NET_DESC).find(n=>n.includes(q));
  if(net){selectNet(net);const ps=PINS.filter(p=>p.net===net);
    if(ps.length){centerOn(ps.reduce((s,p)=>s+p.x,0)/ps.length,ps.reduce((s,p)=>s+p.y,0)/ps.length,1000);}return;}
  let ref=Object.keys(COMP).find(r=>r.toUpperCase()===q)||Object.keys(COMP).find(r=>r.toUpperCase().includes(q));
  if(ref){selectComp(ref);return;}
  panel.innerHTML='<h3>یافت نشد</h3><div class="desc">«'+esc(q)+'» — نام نت یا قطعه معتبر نیست.</div>';
}
document.getElementById('sch-go').addEventListener('click',doSearch);
document.getElementById('sch-search').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch();});
defaultPanel();applyVB();
window.__sch={selectNet:selectNet,selectComp:selectComp,pins:PINS.length,nets:Object.keys(NET_DESC).length,comps:Object.keys(COMP).length};
})();
</script>'''

html = (TEMPLATE
        .replace('__SVG__', SVG)
        .replace('__PINS__', PINS_JSON)
        .replace('__TAGS__', TAGS_JSON)
        .replace('__WIRES__', WIRES_JSON)
        .replace('__COMP__', COMP_JSON)
        .replace('__NETDESC__', NETDESC_JSON)
        .replace('__NETCOL__', NETCOL_JSON)
        .replace('__REGIONS__', REG_JSON)
        .replace('__SW__', str(SHEET_W))
        .replace('__SH__', str(SHEET_H)))

if '--lab' in sys.argv:
    with open(os.path.join(OUT, 'lab_ui.html'), encoding='utf-8') as f:
        lab = f.read()
    with open(os.path.join(OUT, '..', 'sim', 'circuit_engine.js'), encoding='utf-8') as f:
        engine = f.read()
    replacements = {
        '__SVG__': SVG, '__ENGINE__': engine, '__COMP__': COMP_JSON,
        '__PINS__': PINS_JSON, '__NETDESC__': NETDESC_JSON, '__REGIONS__': REG_JSON,
    }
    for token, value in replacements.items():
        lab = lab.replace(token, value)
    lab_path = os.path.join(OUT, 'circuit_lab.html')
    with open(lab_path, 'w', encoding='utf-8') as f:
        f.write(lab)
    print('lab coverage:', len(S.pins), 'pins;', len(comps), 'components')
    print('OK:', lab_path)
    sys.exit(0)

frag_path = os.path.join(OUT, 'circuit_schematic_frag.html')
with open(frag_path, 'w', encoding='utf-8') as f:
    f.write(html)
standalone = ('<!DOCTYPE html>\n<html lang="fa" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
              '<title>\u0646\u0642\u0634\u0647 \u06a9\u0627\u0645\u0644 \u0645\u062f\u0627\u0631 \u0633\u0627\u0639\u062a \u062f\u06cc\u062c\u06cc\u062a\u0627\u0644</title>\n'
              '</head>\n<body style="margin:0;background:#0d1117">\n' + html + '\n</body>\n</html>\n')
std_path = os.path.join(OUT, 'circuit_schematic.html')
with open(std_path, 'w', encoding='utf-8') as f:
    f.write(standalone)

print('pins drawn:', len(S.pins), '(CSV pins:', len(csv_pins), ') — coverage OK')
print('nets:', len(netdesc), 'components:', len(comps), 'tags:', len(S.tags), 'wires:', len(S.wires))
print('standalone bytes:', os.path.getsize(std_path), 'fragment bytes:', os.path.getsize(frag_path))
print('OK:', std_path)