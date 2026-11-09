# -*- coding: utf-8 -*-
"""All-discrete transistor clock netlist generator.

Single source of truth for every pin -> net assignment. Stamps repeated cells:
  Pierce oscillator, 15 divider TFFs, Schmitt triggers, 6 digit cells
  (4-bit TFF counter + reset decode + diode-matrix 7seg decoder + EF drivers),
  carry/24-reset DTL logic, SET toggle, 5 debounced buttons, POR, colon, power.

2N3904 TO-92 CASE 29 STYLE 1: pin 1=E, 2=B, 3=C  (ON Semi 2N3903/D Rev.9)
1N4148 DO-35: pin 1=A (anode), pin 2=K (cathode = black band)  (ON Semi 1N914/D)

Emits netlist.csv, nets.csv, bom.csv. Assertions:
  * every (ref,pin) listed exactly once
  * no floating net (every non-NC net has >=2 pins)
  * no wire-OR: no net driven by two active transistor outputs
ANALOG BEHAVIOR IS NOT VERIFIED HERE (needs SPICE + bench). This is connectivity.
"""
import csv, os, io, sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.dirname(os.path.abspath(__file__))

rows = []          # Ref,Model,Value,Package,Pin,PinName,Net,Notes
drivers = set()    # (ref,pin) active logic outputs (collector or EF emitter)
netdesc = {}
seen_pins = set()

def net(name, desc=''):
    if name not in netdesc:
        netdesc[name] = desc or name
    return name

V = net('VCC', '+5V regulated USB rail')
G = net('GND', '0V common ground')
NC = 'NC'

def comp(ref, model, value, pkg, pins, drv=()):
    for n, t in pins.items():
        nm, nt, note = (t + ('',))[:3] if len(t) < 3 else t
        key = (ref, str(n))
        assert key not in seen_pins, 'duplicate pin %s' % (key,)
        seen_pins.add(key)
        rows.append([ref, model, value, pkg, str(n), nm, nt, note])
    for n in drv:
        drivers.add((ref, str(n)))

def R(ref, val, a, b, note=''):
    comp(ref, 'resistor', val, 'AXIAL-0.25W', {1: ('1', a, note), 2: ('2', b, '')})

def C(ref, val, a, b, note=''):
    comp(ref, 'capacitor', val, 'RADIAL', {1: ('1', a, note), 2: ('2', b, '')})

def D(ref, a, k, note=''):
    comp(ref, '1N4148', '-', 'DO-35', {1: ('A', a, note), 2: ('K', k, '')})

def Q(ref, e, b, c, note='', drv=()):
    comp(ref, '2N3904', '-', 'TO-92', {1: ('E', e, note), 2: ('B', b, ''), 3: ('C', c, '')}, drv)

# ---------------------------------------------------------------------------
# Reusable cells
# ---------------------------------------------------------------------------
def tff(pfx, clk, reset_net, preset=False):
    """Bistable toggle flip-flop. Returns (Q, QN) collector nets."""
    QA = net(pfx + '_QA', pfx + ' bit Q (Q1 collector)')
    QB = net(pfx + '_QB', pfx + ' bit QN (Q2 collector)')
    B1 = net(pfx + '_B1', pfx + ' base Q1')
    B2 = net(pfx + '_B2', pfx + ' base Q2')
    RN = net(pfx + '_RSTN', pfx + ' reset injection node')
    Q(pfx + '_Q1', G, B1, QA, 'TFF half A', (3,))
    Q(pfx + '_Q2', G, B2, QB, 'TFF half B', (3,))
    R(pfx + '_RCA', '2.2k', V, QA)
    R(pfx + '_RCB', '2.2k', V, QB)
    R(pfx + '_RXA', '22k', QA, B2)
    R(pfx + '_RXB', '22k', QB, B1)
    R(pfx + '_RBA', '47k', B1, G)
    R(pfx + '_RBB', '47k', B2, G)
    C(pfx + '_CCA', '100pF', QA, B2, 'speed/steering cap')
    C(pfx + '_CCB', '100pF', QB, B1, 'speed/steering cap')
    D(pfx + '_DS1', clk, B1, 'steering anode=clk cathode=base')
    D(pfx + '_DS2', clk, B2, 'steering anode=clk cathode=base')
    R(pfx + '_RS', '100k', clk, V, 'clock pull-up')
    D(pfx + '_DRST', reset_net, RN, 'preset Q=1' if preset else 'clear Q=0')
    R(pfx + '_RRST', '10k', RN, B2 if preset else B1, 'reset base-current limit')
    return QA, QB

def nand2(pfx, inA, inB, out):
    """DTL NAND2: input diodes + level shift + NPN. out = collector (active)."""
    X = net(pfx + '_X', pfx + ' DTL input node')
    B = net(pfx + '_B', pfx + ' DTL base')
    R(pfx + '_RU', '10k', V, X)
    D(pfx + '_DA', X, inA, 'anode=X cathode=input')
    D(pfx + '_DB', X, inB, 'anode=X cathode=input')
    D(pfx + '_DL', X, B, 'level shift')
    R(pfx + '_RB', '22k', B, G)
    R(pfx + '_RC', '2.2k', V, out)
    Q(pfx + '_Q', G, B, out, 'DTL NPN', (3,))

def inv(pfx, inp, out):
    """DTL inverter (one input diode)."""
    X = net(pfx + '_X', pfx + ' DTL input node')
    B = net(pfx + '_B', pfx + ' DTL base')
    R(pfx + '_RU', '10k', V, X)
    D(pfx + '_DA', X, inp, 'anode=X cathode=input')
    D(pfx + '_DL', X, B, 'level shift')
    R(pfx + '_RB', '22k', B, G)
    R(pfx + '_RC', '2.2k', V, out)
    Q(pfx + '_Q', G, B, out, 'DTL NPN', (3,))

def and2(pfx, inA, inB, out):
    """AND2 = NAND2 + INV."""
    n = net(pfx + '_N', pfx + ' NAND intermediate')
    nand2(pfx + '_n', inA, inB, n)
    inv(pfx + '_i', n, out)

def diode_or(pfx, inputs, out, pd='10k'):
    """Allowed diode-OR (NOT wire-OR): anodes=inputs, cathode=out, pull-down."""
    R(pfx + '_PD', pd, out, G)
    for i, inp in enumerate(inputs):
        D(pfx + '_d%d' % i, inp, out, 'OR anode=input cathode=out')

def ef(pfx, inp, out):
    """NPN emitter-follower buffer (low-impedance source). out = emitter."""
    E = net(pfx + '_E', pfx + ' EF emitter')
    Q(pfx + '_Q', E, inp, V, 'emitter follower', (1,))
    R(pfx + '_RE', '1k', E, G, 'EF pull-down')
    # out taken from emitter through nothing (direct low-Z); connect E to out:
    # use a 0-ohm link net alias by tying out=E caller-side; here out is separate
    R(pfx + '_RO', '0R', E, out, 'EF output link')

def schmitt(pfx, inp, out):
    """Emitter-coupled Schmitt trigger (2 NPN). Non-inverting buffer w/ hysteresis."""
    Ba = net(pfx + '_Ba', pfx + ' Qa base')
    Ca = net(pfx + '_Ca', pfx + ' Qa collector')
    Cb = net(pfx + '_Cb', pfx + ' Qb base')
    Ee = net(pfx + '_Ee', pfx + ' common emitter')
    R(pfx + '_Rin', '10k', inp, Ba)
    Q(pfx + '_Qa', Ee, Ba, Ca, 'Schmitt Qa', (3,))
    Q(pfx + '_Qb', Ee, Cb, out, 'Schmitt Qb', (3,))
    R(pfx + '_Rc1', '2.2k', V, Ca)
    R(pfx + '_Rc2', '2.2k', V, out)
    R(pfx + '_Rcp', '10k', Ca, Cb)
    R(pfx + '_Rb2', '22k', Cb, G)
    R(pfx + '_Re', '1k', Ee, G)

# ---------------------------------------------------------------------------
# 1) Pierce crystal oscillator (1x 2N3904)
# ---------------------------------------------------------------------------
CLK32K = net('CLK32K', '32.768kHz Pierce oscillator output')
XTAL_A = net('XTAL_A', 'crystal node A = base side')
XTAL_B = net('XTAL_B', 'crystal node B = collector side')
OSC_E = net('OSC_E', 'oscillator emitter')
Q('OSC_Q', OSC_E, XTAL_A, XTAL_B, 'Pierce oscillator NPN', (3,))
R('OSC_RF', '1M', XTAL_B, XTAL_A, 'feedback bias')
R('OSC_RD', '2.2k', V, XTAL_B, 'collector load')
R('OSC_RE', '1k', OSC_E, G, 'emitter bias')
C('OSC_C1', '22pF', XTAL_A, G, 'crystal load')
C('OSC_C2', '22pF', XTAL_B, G, 'crystal load')
comp('Y1', 'crystal', '32.768kHz', 'HC-49S', {1: ('1', XTAL_A, 'CL=12.5pF'), 2: ('2', XTAL_B, '')})
D('OSC_D1', XTAL_A, G, 'clamp negative swing')
D('OSC_D2', XTAL_B, V, 'clamp to rail')
R('OSC_OUT', '10k', XTAL_B, CLK32K, 'output isolation')
R('OSC_OPD', '10k', CLK32K, G, 'output pull-down')

# ---------------------------------------------------------------------------
# 2) 15-stage ripple divider /32768 -> 1Hz
# ---------------------------------------------------------------------------
RST_GLOBAL = net('RST_GLOBAL', 'global reset bus (active HIGH, buffered)')
clk = CLK32K
div_q = []
for k in range(1, 16):
    pfx = 'DIV%d' % k
    q, qn = tff(pfx, clk, RST_GLOBAL, preset=(k == 15))
    div_q.append(q)
    clk = q
CLK1HZ_RAW = div_q[-1]
CLK1HZ = net('CLK1HZ', 'clean 1Hz after Schmitt; first rising edge t=1.000s')
schmitt('SCH_1HZ', CLK1HZ_RAW, CLK1HZ)

# ---------------------------------------------------------------------------
# 3) Buttons + debounce (5) + SET toggle + POR
# ---------------------------------------------------------------------------
def button(name):
    raw = net('BTN_%s_RAW' % name, name + ' raw node (HIGH while pressed)')
    out = net('BTN_%s' % name, name + ' debounced pulse (active HIGH)')
    comp('SW_%s' % name, 'tact switch', 'SPST-NO', '6x6mm',
         {1: ('1', V, ''), 2: ('2', raw, 'press -> HIGH')})
    R('R_%s_PD' % name, '100k', raw, G, 'pull-down')
    C('C_%s' % name, '100nF', raw, G, 'debounce')
    schmitt('SCH_%s' % name, raw, out)
    return out

BTN_SET = button('SET')
BTN_HOUR = button('HOUR')
BTN_MIN = button('MIN')
BTN_SECRST = button('SECRST')
BTN_MSTRST = button('MSTRST')

# SET mode toggle
SET_MODE = net('SET_MODE', '1 = set mode')
nSET_MODE = net('nSET_MODE', 'inverted SET_MODE')
sm_q, sm_qn = tff('SET_FF', BTN_SET, RST_GLOBAL)
# alias SET_MODE/nSET_MODE to the toggle outputs via 0R links
R('SET_LQ', '0R', sm_q, SET_MODE, 'link')
R('SET_LQN', '0R', sm_qn, nSET_MODE, 'link')

# POR: HIGH at power-up, decays LOW (tau ~ 1s)
POR_N = net('POR_N', 'POR RC node (HIGH at power-up)')
POR_RAW = net('POR_RAW', 'POR Schmitt output')
R('R_POR', '100k', POR_N, G, 'POR discharge')
C('C_POR', '10uF', POR_N, V, 'POR charge (HIGH at startup)')
D('D_POR', POR_N, V, 'fast discharge clamp')
schmitt('SCH_POR', POR_N, POR_RAW)

# RST_GLOBAL = (POR_RAW OR BTN_MSTRST) buffered by EF
RST_OR = net('RST_OR', 'POR OR master-reset (diode-OR)')
diode_or('RST_OR', [POR_RAW, BTN_MSTRST], RST_OR)
ef('RST_BUF', RST_OR, RST_GLOBAL)

# ---------------------------------------------------------------------------
# 4) Segment decoder equations (verified 0-9 in sim/verify.js)
# ---------------------------------------------------------------------------
# literal names: Q0..Q3, N0..N3 (complement). term = list of literals (AND).
UNITS_EQ = {
    'a': [['Q3'], ['Q1'], ['Q2', 'Q0'], ['N2', 'N0']],
    'b': [['N2'], ['N1', 'N0'], ['Q1', 'Q0']],
    'c': [['Q2'], ['N1'], ['Q0']],
    'd': [['Q3'], ['N2', 'N0'], ['N2', 'Q1'], ['Q1', 'N0'], ['Q2', 'N1', 'Q0']],
    'e': [['N2', 'N0'], ['Q1', 'N0']],
    'f': [['Q3'], ['Q2', 'N1'], ['Q2', 'N0'], ['N1', 'N0']],
    'g': [['Q3'], ['Q2', 'N1'], ['Q2', 'N0'], ['N2', 'Q1']],
}
HT_EQ = {
    'a': [['N0']], 'b': [['ONE']], 'c': [['N1']], 'd': [['N0']],
    'e': [['N0']], 'f': [['N1', 'N0']], 'g': [['Q1', 'N0']],
}
# display SC52-11EWA pinout (common cathode): COM=3,8; a=7,b=6,c=4,d=2,e=1,f=9,g=10,DP=5
SEG_PIN = {'a': 7, 'b': 6, 'c': 4, 'd': 2, 'e': 1, 'f': 9, 'g': 10}

def seg_decoder(dig, bits, eqs):
    """bits = [(Q0,QN0),...,(Q3,QN3)]. Diode-matrix AND terms -> diode-OR -> EF -> display."""
    lit = {}
    for i, (q, qn) in enumerate(bits):
        lit['Q%d' % i] = q
        lit['N%d' % i] = qn
    lit['ONE'] = V   # constant HIGH (segment always on)
    for seg in 'abcdefg':
        terms = eqs[seg]
        term_nodes = []
        for ti, term in enumerate(terms):
            if len(term) == 1:
                term_nodes.append(lit[term[0]])
            else:
                node = net('%s_%s_t%d' % (dig, seg, ti), '%s seg %s AND term %d' % (dig, seg, ti))
                R('%s_%s_t%d_PU' % (dig, seg, ti), '10k', V, node)
                for lj, l in enumerate(term):
                    D('%s_%s_t%d_d%d' % (dig, seg, ti, lj), node, lit[l], 'AND anode=node cathode=lit')
                term_nodes.append(node)
        segn = net('%s_SEG_%s' % (dig, seg), '%s segment %s diode-OR node' % (dig, seg))
        R('%s_%s_PD' % (dig, seg), '10k', segn, G)
        for ti, node in enumerate(term_nodes):
            D('%s_%s_or%d' % (dig, seg, ti), node, segn, 'OR anode=term cathode=seg')
        # emitter-follower driver + 330R to display anode
        E = net('%s_%s_E' % (dig, seg), '%s seg %s driver emitter' % (dig, seg))
        dsp = net('%s_DSP_%s' % (dig, seg), '%s seg %s display anode' % (dig, seg))
        Q('%s_DRV_%s' % (dig, seg), E, segn, V, 'segment EF driver', (1,))
        R('%s_DRV_%s_R' % (dig, seg), '330R', E, dsp, 'segment current limit ~7mA')
    # display component
    dp = net('%s_DP' % dig, '%s decimal point (unused)' % dig)
    pins = {3: ('COM', G, 'common cathode'), 8: ('COM', G, 'common cathode'),
            5: ('DP', dp, 'unused')}
    for s, p in SEG_PIN.items():
        pins[p] = (s, '%s_DSP_%s' % (dig, s), '')
    comp('DS_%s' % dig, 'SC52-11EWA', 'red 0.52in', '10-pin', pins)
    R('%s_DP_R' % dig, '10k', dp, G, 'DP pull-down (off)')

# ---------------------------------------------------------------------------
# 5) Six digit cells + carry / reset / clock logic
# ---------------------------------------------------------------------------
def digit(dig, clk_net, reset_bus, mod, eqs):
    """Stamp 4 TFF bits + reset decode + decoder. Returns (bits, decode_net)."""
    bits = []
    c = clk_net
    for b in range(4):
        q, qn = tff('%s_b%d' % (dig, b), c, reset_bus)
        bits.append((q, qn))
        c = q  # ripple: next bit clocked by this Q falling edge
    # reset decode
    if mod == 10:
        dec = net('%s_R10' % dig, '%s = 1010 decode (Q3.Q1)' % dig)
        and2('%s_DEC' % dig, bits[3][0], bits[1][0], dec)
    elif mod == 6:
        dec = net('%s_R6' % dig, '%s = 0110 decode (Q2.Q1)' % dig)
        and2('%s_DEC' % dig, bits[2][0], bits[1][0], dec)
    elif mod == 3:
        dec = net('%s_R3' % dig, '%s = 0011 decode (Q1.Q0)' % dig)
        and2('%s_DEC' % dig, bits[1][0], bits[0][0], dec)
    else:
        dec = None
    seg_decoder(dig, bits, eqs)
    return bits, dec

# clock gating for seconds (run only when not in SET mode)
CLK_SEC = net('CLK_SEC', 'CLK1HZ gated by nSET_MODE -> SU clock')
and2('G_CLKSEC', CLK1HZ, nSET_MODE, CLK_SEC)

# SET-mode manual clocks
HOUR_GATE = net('HOUR_GATE', 'BTN_HOUR AND SET_MODE')
MIN_GATE = net('MIN_GATE', 'BTN_MIN AND SET_MODE')
and2('G_HOUR', BTN_HOUR, SET_MODE, HOUR_GATE)
and2('G_MIN', BTN_MIN, SET_MODE, MIN_GATE)

# seconds reset bus = RST_GLOBAL OR BTN_SECRST
RST_SEC = net('RST_SEC', 'seconds reset (global OR sec-reset button)')
RST_SEC_OR = net('RST_SEC_OR', 'seconds reset diode-OR')
diode_or('RST_SEC_OR', [RST_GLOBAL, BTN_SECRST], RST_SEC_OR)
ef('RST_SEC_BUF', RST_SEC_OR, RST_SEC)

# hours reset bus = RST_GLOBAL OR D24 (D24 defined after digits)
RST_HOURS = net('RST_HOURS', 'hours reset (global OR 24-decode)')
RST_HOURS_OR = net('RST_HOURS_OR', 'hours reset diode-OR')
ef('RST_HOURS_BUF', RST_HOURS_OR, RST_HOURS)

# --- seconds units (SU, MOD-10) ---
SU_RST_OR = net('SU_RST_OR', 'SU reset diode-OR')
SU_RST = net('SU_RST', 'SU reset bus (buffered)')
SU_bits, SU_R10 = digit('SU', CLK_SEC, SU_RST, 10, UNITS_EQ)
diode_or('SU_RST_OR', [RST_SEC, SU_R10], SU_RST_OR)
ef('SU_RST_BUF', SU_RST_OR, SU_RST)
C_SU = SU_R10  # carry to seconds tens

# --- seconds tens (ST, MOD-6) ---
ST_RST_OR = net('ST_RST_OR', 'ST reset diode-OR')
ST_RST = net('ST_RST', 'ST reset bus (buffered)')
ST_bits, ST_R6 = digit('ST', C_SU, ST_RST, 6, UNITS_EQ)
diode_or('ST_RST_OR', [RST_SEC, ST_R6], ST_RST_OR)
ef('ST_RST_BUF', ST_RST_OR, ST_RST)

# --- minutes units (MU, MOD-10) ---
CLK_MU = net('CLK_MU', 'ST_R6 OR MIN_GATE -> MU clock')
CLK_MU_OR = net('CLK_MU_OR', 'MU clock diode-OR')
diode_or('CLK_MU_OR', [ST_R6, MIN_GATE], CLK_MU_OR)
ef('CLK_MU_BUF', CLK_MU_OR, CLK_MU)
MU_RST_OR = net('MU_RST_OR', 'MU reset diode-OR')
MU_RST = net('MU_RST', 'MU reset bus (buffered)')
MU_bits, MU_R10 = digit('MU', CLK_MU, MU_RST, 10, UNITS_EQ)
diode_or('MU_RST_OR', [RST_GLOBAL, MU_R10], MU_RST_OR)
ef('MU_RST_BUF', MU_RST_OR, MU_RST)
C_MU = MU_R10

# --- minutes tens (MT, MOD-6) ---
MT_RST_OR = net('MT_RST_OR', 'MT reset diode-OR')
MT_RST = net('MT_RST', 'MT reset bus (buffered)')
MT_bits, MT_R6 = digit('MT', C_MU, MT_RST, 6, UNITS_EQ)
diode_or('MT_RST_OR', [RST_GLOBAL, MT_R6], MT_RST_OR)
ef('MT_RST_BUF', MT_RST_OR, MT_RST)

# --- hours units (HU, MOD-10) ---
CLK_HU = net('CLK_HU', 'MT_R6 OR HOUR_GATE -> HU clock')
CLK_HU_OR = net('CLK_HU_OR', 'HU clock diode-OR')
diode_or('CLK_HU_OR', [MT_R6, HOUR_GATE], CLK_HU_OR)
ef('CLK_HU_BUF', CLK_HU_OR, CLK_HU)
HU_RST_OR = net('HU_RST_OR', 'HU reset diode-OR')
HU_RST = net('HU_RST', 'HU reset bus (buffered)')
HU_bits, HU_R10 = digit('HU', CLK_HU, HU_RST, 10, UNITS_EQ)
# D24 = HT.Q1 AND HU.Q2  (HT=2, HU=4)
D24 = net('D24', 'hour = 24 decode (HT.Q1 AND HU.Q2)')
# HT bits stamped below; forward-declare HT bit nets by stamping HT first conceptually:
# We stamp HT next, then wire D24 and reset ORs.
C_HU = HU_R10

# --- hours tens (HT, MOD-3, simplified decoder) ---
HT_RST_OR = net('HT_RST_OR', 'HT reset diode-OR')
HT_RST = net('HT_RST', 'HT reset bus (buffered)')
HT_bits, HT_R3 = digit('HT', C_HU, HT_RST, 3, HT_EQ)
diode_or('HT_RST_OR', [RST_HOURS, HT_R3], HT_RST_OR)
ef('HT_RST_BUF', HT_RST_OR, HT_RST)

# now wire D24 and the hours reset ORs (HT bits available)
and2('G_D24', HT_bits[1][0], HU_bits[2][0], D24)
diode_or('RST_HOURS_OR', [RST_GLOBAL, D24], RST_HOURS_OR)
diode_or('HU_RST_OR', [RST_HOURS, HU_R10], HU_RST_OR)
ef('HU_RST_BUF', HU_RST_OR, HU_RST)

# ---------------------------------------------------------------------------
# 6) Colon blink (1Hz) + power decoupling
# ---------------------------------------------------------------------------
COLON_B = net('COLON_B', 'colon driver base via 10k')
COLON_E = net('COLON_E', 'colon driver emitter')
COLON_K = net('COLON_K', 'colon LED cathodes')
COLON_A1 = net('COLON_A1', 'LED1 anode (via 1k)')
COLON_A2 = net('COLON_A2', 'LED2 anode (via 1k)')
R('R_COLON_B', '10k', CLK1HZ, COLON_B)
Q('Q_COLON', COLON_E, COLON_B, COLON_K, 'colon blink NPN', (3,))
R('R_COLON_E', '1k', COLON_E, G)
R('R_COL1', '1k', V, COLON_A1, 'LED1 anode limit')
R('R_COL2', '1k', V, COLON_A2, 'LED2 anode limit')
comp('LED_COL1', 'LED red', 'Vf~2.0V', '5mm', {1: ('A', COLON_A1, ''), 2: ('K', COLON_K, '')})
comp('LED_COL2', 'LED red', 'Vf~2.0V', '5mm', {1: ('A', COLON_A2, ''), 2: ('K', COLON_K, '')})

# power input + decoupling
comp('J1', 'USB power', '5V regulated', 'USB-B', {1: ('VBUS', V, '+5V'), 2: ('GND', G, ''), 3: ('D+', NC, ''), 4: ('D-', NC, '')})
C('C_BULK', '470uF', V, G, 'bulk rail storage')
C('C_IN', '100uF', V, G, 'input electrolytic')
ntrans = sum(1 for r in rows if r[1] == '2N3904' and r[4] == '1')
nbyp = max(1, ntrans // 10)
for i in range(1, nbyp + 1):
    C('C_BYP%d' % i, '100nF', V, G, 'decoupling per ~10 transistors')

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
with open(os.path.join(OUT, 'netlist.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Ref', 'Model', 'Value', 'Package', 'Pin', 'PinName', 'Net', 'Notes'])
    w.writerows(rows)

with open(os.path.join(OUT, 'nets.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Net', 'Description'])
    for k in sorted(netdesc):
        w.writerow([k, netdesc[k]])

# ---------------------------------------------------------------------------
# BOM (exact counts from rows)
# ---------------------------------------------------------------------------
# count unique components (refs), not pins
ref_info = {}
for r in rows:
    ref_info[r[0]] = (r[1], r[2], r[3])   # ref -> (model,value,pkg)
comp_count = Counter(ref_info.values())

bom = []
fa_name = {
    '2N3904': 'ترانزیستور NPN',
    '1N4148': 'دیود سوئیچ',
    'resistor': 'مقاومت',
    'capacitor': 'خازن',
    'crystal': 'کریستال',
    'SC52-11EWA': 'نمایشگر ۷ سگمنت کاتد-مشترک',
    'tact switch': 'کلید tact',
    'LED red': 'LED قرمز',
    'USB power': 'کانکتور تغذیه USB',
}
# group resistors/caps by value for a tidy BOM
for (model, value, pkg), cnt in sorted(comp_count.items(), key=lambda x: (-x[1], x[0])):
    bom.append((fa_name.get(model, model), model, value, cnt, pkg))

with open(os.path.join(OUT, 'bom.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['نام قطعه', 'مدل', 'مقدار', 'تعداد', 'پکیج'])
    for i, b in enumerate(bom, 1):
        w.writerow([i] + list(b))

# ---------------------------------------------------------------------------
# Sanity / coverage assertions
# ---------------------------------------------------------------------------
# 1) every pin listed once (enforced in comp via seen_pins)
# 2) no floating net: every non-NC net has >=2 pins
cnt = Counter(r[6] for r in rows if r[6] != NC)
singles = [n for n, c in cnt.items() if c < 2]
assert not singles, 'floating nets (<2 pins): %s' % singles
# 3) every used net is described
used = set(r[6] for r in rows) - {NC}
unknown = used - set(netdesc)
assert not unknown, 'undescribed nets: %s' % unknown
# 4) no wire-OR: no net driven by 2+ active transistor outputs
drv = Counter(r[6] for r in rows if (r[0], r[4]) in drivers and r[6] != NC)
multi = {n: c for n, c in drv.items() if c > 1}
assert not multi, 'double-driven outputs (wire-OR): %s' % multi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
n_q = sum(1 for r in rows if r[1] == '2N3904' and r[4] == '1')
n_d = sum(1 for r in rows if r[1] == '1N4148' and r[4] == '1')
n_r = sum(1 for r in rows if r[1] == 'resistor' and r[4] == '1')
n_c = sum(1 for r in rows if r[1] == 'capacitor' and r[4] == '1')
n_other = len(seen_pins) and sum(1 for ref in set(r[0] for r in rows)
                                 if next(r[1] for r in rows if r[0] == ref) not in
                                 ('2N3904', '1N4148', 'resistor', 'capacitor'))
total_comp = len(set(r[0] for r in rows))
print('netlist rows (pins):', len(rows))
print('nets:', len(netdesc), 'BOM lines:', len(bom))
print('2N3904:', n_q, ' 1N4148:', n_d, ' resistors:', n_r, ' capacitors:', n_c)
print('total components:', total_comp)
print('active output drivers:', len(drivers))
print('SANITY OK: unique pins, no floating net, no wire-OR of transistor outputs')
print('NOTE: analog behavior UNVERIFIED (needs SPICE + bench). Connectivity only.')