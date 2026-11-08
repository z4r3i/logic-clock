# -*- coding: utf-8 -*-
"""Generates netlist.csv, nets.csv, bom.csv and markdown table fragments.
Single source of truth for every pin -> net assignment of the hardware clock.
"""
import csv, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.dirname(os.path.abspath(__file__))

rows = []   # Ref, Model, Package, Pin, PinName, Net, Notes
def pin(ref, model, pkg, n, name, net, note=''):
    rows.append([ref, model, '-', pkg, str(n), name, net, note])

NC = 'NC'
G = 'GND'
V = 'VCC'

# ---------------- U1 CD4060B ----------------
u1 = {1: ('Q12', NC), 2: ('Q13', NC), 3: ('Q14', 'CLK2HZ'), 4: ('Q6', NC),
      5: ('Q5', NC), 6: ('Q7', NC), 7: ('Q4', NC), 8: ('VSS', G),
      9: ('OSC OUT (phi0)', NC, 'internal osc output; leave open per Fig.13'),
      10: ('OSC OUT/ (phi0bar)', 'OSC_FB', 'to Rs then XTAL_B per Fig.13'),
      11: ('OSC IN (phi1)', 'XTAL_A'), 12: ('RESET', 'RST_GLOBAL', 'active HIGH'),
      13: ('Q9', NC), 14: ('Q8', NC), 15: ('Q10', NC), 16: ('VDD', V)}
for n, t in u1.items():
    pin('U1', 'CD4060B', 'DIP-16', n, t[0], t[1], t[2] if len(t) > 2 else '')

# ---------------- U2 CD4013B ----------------
u2 = {1: ('Q1', 'CLK1HZ'), 2: ('Q1/', 'FF1_D'), 3: ('CLOCK1', 'CLK2HZ_INV'),
      4: ('RESET1', G), 5: ('D1', 'FF1_D'), 6: ('SET1', 'RST_GLOBAL', 'preset Q1=1 during reset => first 1Hz edge at t=1.000s'),
      7: ('VSS', G), 8: ('SET2', G), 9: ('D2', 'FF2_D'), 10: ('RESET2', 'RST_GLOBAL'),
      11: ('CLOCK2', 'BTN_SET'), 12: ('Q2/', 'FF2_D'), 13: ('Q2', 'SET_MODE'), 14: ('VDD', V)}
for n, t in u2.items():
    pin('U2', 'CD4013B', 'DIP-14', n, t[0], t[1], t[2] if len(t) > 2 else '')

# ---------------- U3..U8 CD4026B ----------------
digits = [  # ref, digit, clock, carry, reset, display
    ('U3', 'SU', 'CLK_SEC', 'C_SU', 'RST_SEC', 'DS6'),
    ('U4', 'ST', 'C_SU', NC, 'RST_ST', 'DS5'),
    ('U5', 'MU', 'CLK_MU', 'C_MU', 'RST_GLOBAL', 'DS4'),
    ('U6', 'MT', 'C_MU', NC, 'RST_MT', 'DS3'),
    ('U7', 'HU', 'CLK_HU', 'C_HU', 'RST_HOURS', 'DS2'),
    ('U8', 'HT', 'C_HU', NC, 'RST_HOURS', 'DS1'),
]
segpin = {'a': 10, 'b': 12, 'c': 13, 'd': 9, 'e': 11, 'f': 6, 'g': 7}
for ref, dig, clk, carry, rst, ds in digits:
    pin(ref, 'CD4026B', 'DIP-16', 1, 'CLOCK', clk)
    pin(ref, 'CD4026B', 'DIP-16', 2, 'CLOCK INHIBIT', G, 'tie LOW: count on CLOCK rising edge')
    pin(ref, 'CD4026B', 'DIP-16', 3, 'DISPLAY ENABLE IN', V, 'segments always on')
    pin(ref, 'CD4026B', 'DIP-16', 4, 'DISPLAY ENABLE OUT', NC)
    pin(ref, 'CD4026B', 'DIP-16', 5, 'CARRY OUT', carry)
    for s, p in segpin.items():
        pin(ref, 'CD4026B', 'DIP-16', p, 'segment ' + s, 'SEG_%s_%s' % (dig, s.upper()))
    pin(ref, 'CD4026B', 'DIP-16', 8, 'VSS', G)
    pin(ref, 'CD4026B', 'DIP-16', 14, 'UNGATED C', NC)
    pin(ref, 'CD4026B', 'DIP-16', 15, 'RESET', rst, 'active HIGH')
    pin(ref, 'CD4026B', 'DIP-16', 16, 'VDD', V)

# ---------------- U9..U11 CD4081B (quad 2-in AND) ----------------
and_gates = {
    'U9': [(1, 2, 3, 'SEG_ST_E', 'SEG_ST_F', 'ST_EF'),
           (5, 6, 4, 'ST_EF', 'SEG_ST_G', 'D6_ST'),
           (8, 9, 10, 'SEG_MT_E', 'SEG_MT_F', 'MT_EF'),
           (12, 13, 11, 'MT_EF', 'SEG_MT_G', 'D6_MT')],
    'U10': [(1, 2, 3, 'SEG_HT_A', 'SEG_HT_D', 'HT_AD'),
            (5, 6, 4, 'HT_AD', 'SEG_HT_G', 'HT2'),
            (8, 9, 10, 'SEG_HU_C', 'SEG_HU_F', 'HU_CF'),
            (12, 13, 11, 'HU_CF', 'SEG_HU_G', 'HU4')],
    'U11': [(1, 2, 3, 'HT2', 'HU4', 'D24'),
            (5, 6, 4, 'CLK1HZ', 'nSET_MODE', 'CLK_SEC'),
            (8, 9, 10, 'BTN_HOUR', 'SET_MODE', 'HOUR_GATE'),
            (12, 13, 11, 'BTN_MIN', 'SET_MODE', 'MIN_GATE')],
}
for ref, gs in and_gates.items():
    for a, b, o, na, nb, no in gs:
        pin(ref, 'CD4081B', 'DIP-14', a, 'AND in A', na)
        pin(ref, 'CD4081B', 'DIP-14', b, 'AND in B', nb)
        pin(ref, 'CD4081B', 'DIP-14', o, 'AND out Y', no)
    pin(ref, 'CD4081B', 'DIP-14', 7, 'VSS', G)
    pin(ref, 'CD4081B', 'DIP-14', 14, 'VDD', V)

# ---------------- U12..U13 CD4071B (quad 2-in OR) ----------------
or_gates = {
    'U12': [(1, 2, 3, 'RST_GLOBAL', 'BTN_SECRST', 'RST_SEC'),
            (5, 6, 4, 'RST_GLOBAL', 'D24', 'RST_HOURS'),
            (8, 9, 10, 'RST_SEC', 'D6_ST', 'RST_ST'),
            (12, 13, 11, 'RST_GLOBAL', 'D6_MT', 'RST_MT')],
    'U13': [(1, 2, 3, 'POR_RST', 'BTN_MSTRST', 'RST_GLOBAL'),
            (5, 6, 4, 'D6_ST', 'MIN_GATE', 'CLK_MU'),
            (8, 9, 10, 'D6_MT', 'HOUR_GATE', 'CLK_HU'),
            (12, 13, 11, G, G, NC)],
}
for ref, gs in or_gates.items():
    for a, b, o, na, nb, no in gs:
        note = 'unused gate: inputs tied LOW' if no == NC else ''
        pin(ref, 'CD4071B', 'DIP-14', a, 'OR in A', na, note)
        pin(ref, 'CD4071B', 'DIP-14', b, 'OR in B', nb, note)
        pin(ref, 'CD4071B', 'DIP-14', o, 'OR out Y', no, note)
    pin(ref, 'CD4071B', 'DIP-14', 7, 'VSS', G)
    pin(ref, 'CD4071B', 'DIP-14', 14, 'VDD', V)

# ---------------- U14..U15 CD4093B (quad Schmitt NAND, wired as inverters) ----------------
nand_gates = {
    'U14': [(1, 2, 3, 'BTN_SET_n', 'BTN_SET'),
            (5, 6, 4, 'BTN_HOUR_n', 'BTN_HOUR'),
            (8, 9, 10, 'BTN_MIN_n', 'BTN_MIN'),
            (12, 13, 11, 'BTN_SECRST_n', 'BTN_SECRST')],
    'U15': [(1, 2, 3, 'BTN_MSTRST_n', 'BTN_MSTRST'),
            (5, 6, 4, 'SET_MODE', 'nSET_MODE'),
            (8, 9, 10, 'POR_N', 'POR_RST'),
            (12, 13, 11, 'CLK2HZ', 'CLK2HZ_INV')],
}
for ref, gs in nand_gates.items():
    for a, b, o, ni, no in gs:
        pin(ref, 'CD4093B', 'DIP-14', a, 'Schmitt NAND in A', ni, 'inputs tied => inverter')
        pin(ref, 'CD4093B', 'DIP-14', b, 'Schmitt NAND in B', ni, 'inputs tied => inverter')
        pin(ref, 'CD4093B', 'DIP-14', o, 'Schmitt NAND out Y', no)
    pin(ref, 'CD4093B', 'DIP-14', 7, 'VSS', G)
    pin(ref, 'CD4093B', 'DIP-14', 14, 'VDD', V)

# ---------------- U16 7805 + Q1 2N3904 ----------------
pin('U16', 'MC7805/LM7805', 'TO-220', 1, 'INPUT', 'VIN2')
pin('U16', 'MC7805/LM7805', 'TO-220', 2, 'GROUND', G, 'tab = pin 2')
pin('U16', 'MC7805/LM7805', 'TO-220', 3, 'OUTPUT', V)
pin('Q1', '2N3904', 'TO-92', 1, 'E', G)
pin('Q1', '2N3904', 'TO-92', 2, 'B', 'COLON_B')
pin('Q1', '2N3904', 'TO-92', 3, 'C', 'COLON_K')

# ---------------- passives / displays / switches ----------------
prows = []  # Ref, Model, Value, Package, Pin, PinName, Net, Notes
def pp(ref, model, val, pkg, n, name, net, note=''):
    prows.append([ref, model, val, pkg, str(n), name, net, note])

# crystal oscillator passives
pp('Y1', 'crystal 32.768kHz', 'CL=12.5pF', 'HC-49/S or cylinder', 1, '-', 'XTAL_A')
pp('Y1', 'crystal 32.768kHz', 'CL=12.5pF', 'HC-49/S or cylinder', 2, '-', 'XTAL_B')
pp('C1', 'cap ceramic NP0', '18pF', 'radial', 1, '-', 'XTAL_A')
pp('C1', 'cap ceramic NP0', '18pF', 'radial', 2, '-', G)
pp('C2', 'cap ceramic NP0', '18pF', 'radial', 1, '-', 'XTAL_B')
pp('C2', 'cap ceramic NP0', '18pF', 'radial', 2, '-', G)
pp('R_C', 'resistor', '10M', '0.25W', 1, '-', 'XTAL_A')
pp('R_C', 'resistor', '10M', '0.25W', 2, '-', 'XTAL_B')
pp('R_S', 'resistor', '220k', '0.25W', 1, '-', 'XTAL_B')
pp('R_S', 'resistor', '220k', '0.25W', 2, '-', 'OSC_FB')

# segment resistors + displays
disppin = {'a': 7, 'b': 6, 'c': 4, 'd': 2, 'e': 1, 'f': 9, 'g': 10}
for ref, dig, clk, carry, rst, ds in digits:
    for s in 'abcdefg':
        rr = 'R_%s%s' % (dig, s.upper())
        pp(rr, 'resistor', '470R', '0.25W', 1, '-', 'SEG_%s_%s' % (dig, s.upper()))
        pp(rr, 'resistor', '470R', '0.25W', 2, '-', 'DSP_%s_%s' % (dig, s.upper()))
    for s, p in disppin.items():
        pp(ds, 'SC52-11EWA', 'CC red 0.52in', '10-pin', p, s, 'DSP_%s_%s' % (dig, s.upper()))
    pp(ds, 'SC52-11EWA', 'CC red 0.52in', '10-pin', 3, 'COM', G, 'common cathode')
    pp(ds, 'SC52-11EWA', 'CC red 0.52in', '10-pin', 8, 'COM', G, 'common cathode')
    pp(ds, 'SC52-11EWA', 'CC red 0.52in', '10-pin', 5, 'DP', NC)

# buttons: 5x (switch + 100k pull-up + 1uF)
buttons = [('SET', 'SW_SET', 'R_PU_SET', 'C_BTN_SET'),
           ('HOUR', 'SW_HOUR', 'R_PU_HOUR', 'C_BTN_HOUR'),
           ('MIN', 'SW_MIN', 'R_PU_MIN', 'C_BTN_MIN'),
           ('SECRST', 'SW_SECRST', 'R_PU_SECRST', 'C_BTN_SECRST'),
           ('MSTRST', 'SW_MSTRST', 'R_PU_MSTRST', 'C_BTN_MSTRST')]
for name, sw, rp, cb in buttons:
    raw = 'BTN_%s_n' % name
    pp(sw, 'tact switch 6x6', 'SPST-NO', '4-pin', 1, '-', raw, 'pins 1-2 joined')
    pp(sw, 'tact switch 6x6', 'SPST-NO', '4-pin', 2, '-', raw, 'pins 1-2 joined')
    pp(sw, 'tact switch 6x6', 'SPST-NO', '4-pin', 3, '-', G, 'pins 3-4 joined')
    pp(sw, 'tact switch 6x6', 'SPST-NO', '4-pin', 4, '-', G, 'pins 3-4 joined')
    pp(rp, 'resistor', '100k', '0.25W', 1, '-', V)
    pp(rp, 'resistor', '100k', '0.25W', 2, '-', raw)
    pp(cb, 'cap ceramic', '1uF', 'radial', 1, '-', raw)
    pp(cb, 'cap ceramic', '1uF', 'radial', 2, '-', G)

# POR
pp('R_POR', 'resistor', '100k', '0.25W', 1, '-', V)
pp('R_POR', 'resistor', '100k', '0.25W', 2, '-', 'POR_N')
pp('C_POR', 'cap electrolytic', '10uF', 'radial', 1, '+', 'POR_N')
pp('C_POR', 'cap electrolytic', '10uF', 'radial', 2, '-', G)
pp('D2', '1N4148', '-', 'DO-35', 1, 'A', 'POR_N', 'discharge on power-down')
pp('D2', '1N4148', '-', 'DO-35', 2, 'K', V)

# colon
pp('R_CB', 'resistor', '10k', '0.25W', 1, '-', 'CLK1HZ')
pp('R_CB', 'resistor', '10k', '0.25W', 2, '-', 'COLON_B')
pp('R_CL1', 'resistor', '1k', '0.25W', 1, '-', V)
pp('R_CL1', 'resistor', '1k', '0.25W', 2, '-', 'COLON_A1')
pp('R_CL2', 'resistor', '1k', '0.25W', 1, '-', V)
pp('R_CL2', 'resistor', '1k', '0.25W', 2, '-', 'COLON_A2')
pp('LED1', 'LED red', 'Vf~2.0V', '5mm', 1, 'A', 'COLON_A1')
pp('LED1', 'LED red', 'Vf~2.0V', '5mm', 2, 'K', 'COLON_K')
pp('LED2', 'LED red', 'Vf~2.0V', '5mm', 1, 'A', 'COLON_A2')
pp('LED2', 'LED red', 'Vf~2.0V', '5mm', 2, 'K', 'COLON_K')

# power input & regulator caps
pp('J1', 'DC jack / terminal', '9-12V in', '2-pin', 1, '+', 'VIN')
pp('J1', 'DC jack / terminal', '9-12V in', '2-pin', 2, '-', G)
pp('D1', '1N4007', '-', 'DO-41', 1, 'A', 'VIN', 'reverse-polarity protection')
pp('D1', '1N4007', '-', 'DO-41', 2, 'K', 'VIN2')
pp('C_IN1', 'cap ceramic/film', '0.33uF', 'radial', 1, '-', 'VIN2')
pp('C_IN1', 'cap ceramic/film', '0.33uF', 'radial', 2, '-', G)
pp('C_IN2', 'cap electrolytic', '100uF', 'radial', 1, '+', 'VIN2')
pp('C_IN2', 'cap electrolytic', '100uF', 'radial', 2, '-', G)
pp('C_OUT1', 'cap ceramic', '100nF', 'radial', 1, '-', V)
pp('C_OUT1', 'cap ceramic', '100nF', 'radial', 2, '-', G)
pp('C_OUT2', 'cap electrolytic', '100uF', 'radial', 1, '+', V)
pp('C_OUT2', 'cap electrolytic', '100uF', 'radial', 2, '-', G)
pp('C_BULK', 'cap electrolytic', '470uF', 'radial', 1, '+', V)
pp('C_BULK', 'cap electrolytic', '470uF', 'radial', 2, '-', G)
for i in range(1, 16):
    pp('C_BYP%d' % i, 'cap ceramic', '100nF', 'radial', 1, '-', V, 'at U%d VDD' % i)
    pp('C_BYP%d' % i, 'cap ceramic', '100nF', 'radial', 2, '-', G, 'at U%d VSS' % i)

# ---------------- write CSVs ----------------
with open(os.path.join(OUT, 'netlist.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Ref', 'Model', 'Value', 'Package', 'Pin', 'PinName', 'Net', 'Notes'])
    w.writerows(rows)
    w.writerows(prows)

netdesc = {
    'VCC': '+5V regulated rail', 'GND': '0V common ground', 'VIN': 'raw 9-12V input at connector',
    'VIN2': 'after reverse-protection diode D1, regulator input',
    'XTAL_A': 'crystal node A = U1 pin 11 (osc in)', 'XTAL_B': 'crystal node B = C2/Rc/Rs junction',
    'OSC_FB': 'U1 pin 10 to Rs (osc feedback)', 'CLK2HZ': 'U1 Q14 = 2Hz',
    'CLK2HZ_INV': 'inverted Q14 (U15/4) = clock of divide-by-2 FF',
    'CLK1HZ': 'exact 1Hz, first rising edge t=1.000s after reset release',
    'SET_MODE': '1 = set mode (U2 Q2)', 'nSET_MODE': 'inverted SET_MODE',
    'BTN_SET': 'debounced SET pulse (active HIGH)', 'BTN_HOUR': 'debounced HOUR+ pulse',
    'BTN_MIN': 'debounced MIN+ pulse', 'BTN_SECRST': 'debounced seconds-zero pulse',
    'BTN_MSTRST': 'debounced master-reset pulse',
    'BTN_SET_n': 'raw SET node (pull-up + cap, LOW while pressed)',
    'BTN_HOUR_n': 'raw HOUR+ node', 'BTN_MIN_n': 'raw MIN+ node',
    'BTN_SECRST_n': 'raw SEC RESET node', 'BTN_MSTRST_n': 'raw MASTER RESET node',
    'POR_N': 'power-on reset RC node (LOW at power-up)', 'POR_RST': 'POR pulse active HIGH ~0.87s',
    'RST_GLOBAL': 'POR OR master reset; resets divider, FFs, SU, MU',
    'RST_SEC': 'RST_GLOBAL OR BTN_SECRST -> SU reset', 'RST_ST': 'RST_SEC OR D6_ST -> ST reset',
    'RST_MT': 'RST_GLOBAL OR D6_MT -> MT reset', 'RST_HOURS': 'RST_GLOBAL OR D24 -> HU+HT reset',
    'D6_ST': 'seconds-tens = 6 decode (e.f.g); reset+carry pulse',
    'D6_MT': 'minutes-tens = 6 decode (e.f.g); reset+carry pulse',
    'D24': 'hour = 24 decode (HT2 AND HU4); reset pulse',
    'ST_EF': 'ST e AND f', 'MT_EF': 'MT e AND f', 'HT_AD': 'HT a AND d', 'HT2': 'HT = 2 decode',
    'HU_CF': 'HU c AND f', 'HU4': 'HU = 4 decode',
    'CLK_SEC': 'CLK1HZ gated by nSET_MODE -> SU clock',
    'CLK_MU': 'D6_ST OR MIN_GATE -> MU clock', 'CLK_HU': 'D6_MT OR HOUR_GATE -> HU clock',
    'HOUR_GATE': 'BTN_HOUR AND SET_MODE', 'MIN_GATE': 'BTN_MIN AND SET_MODE',
    'C_SU': 'SU carry (1/10 Hz) -> ST clock', 'C_MU': 'MU carry -> MT clock',
    'C_HU': 'HU carry -> HT clock', 'FF1_D': 'U2 Q1/ tied to D1 (toggle)',
    'FF2_D': 'U2 Q2/ tied to D2 (toggle)', 'COLON_B': 'Q1 base via 10k',
    'COLON_K': 'colon LED cathodes = Q1 collector', 'COLON_A1': 'LED1 anode via 1k',
    'COLON_A2': 'LED2 anode via 1k', 'NC': 'not connected',
}
for ref, dig, clk, carry, rst, ds in digits:
    for s in 'abcdefg':
        netdesc['SEG_%s_%s' % (dig, s.upper())] = '%s segment %s (IC pin)' % (dig, s)
        netdesc['DSP_%s_%s' % (dig, s.upper())] = '%s segment %s (display side of 470R)' % (dig, s)
with open(os.path.join(OUT, 'nets.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Net', 'Description'])
    for k in sorted(netdesc):
        w.writerow([k, netdesc[k]])

# ---------------- BOM ----------------
bom = [
    ('U1', 'شمارنده/تقسیم‌کننده ۱۴ مرحله با اسیلاتور', 'CD4060B', '-', 1, 'DIP-16', 'منبع زمان؛ Q14=2Hz'),
    ('U2', 'فلیپ‌فلاپ D دوگانه', 'CD4013B', '-', 1, 'DIP-14', 'FF1 تقسیم بر ۲؛ FF2 تاگل حالت SET'),
    ('U3-U8', 'شمارنده دهدهی + درایور ۷ سگمنت', 'CD4026B', '-', 6, 'DIP-16', 'SU,ST,MU,MT,HU,HT'),
    ('U9-U11', 'چهار گیت AND دو ورودی', 'CD4081B', '-', 3, 'DIP-14', 'دیکود 6/6/24 و گیت‌های کلاک'),
    ('U12-U13', 'چهار گیت OR دو ورودی', 'CD4071B', '-', 2, 'DIP-14', 'جمع ریست/کری؛ یک گیت U13 بلااستفاده'),
    ('U14-U15', 'چهار NAND اشمیت تریگر', 'CD4093B', '-', 2, 'DIP-14', 'دیبانس کلیدها، اینورترها، POR'),
    ('U16', 'رگولاتور ۵ ولت', 'MC7805/LM7805', '-', 1, 'TO-220', 'بدون هیت‌سینک؛ P≈0.44W max'),
    ('Q1', 'ترانزیستور NPN', '2N3904', '-', 1, 'TO-92', 'درایور چشمک‌زن کولن'),
    ('DS1-DS6', 'نمایشگر ۷ سگمنت کاتد مشترک', 'SC52-11EWA', 'قرمز 0.52in', 6, '10-pin', 'COM=3,8؛ a=7,b=6,c=4,d=2,e=1,f=9,g=10,DP=5'),
    ('Y1', 'کریستال ساعت', '32.768kHz', 'CL=12.5pF', 1, 'HC-49S', 'با C1=C2=18pF و Cstray≈3.5pF'),
    ('R_SA..R_SUG', 'مقاومت محدودکننده سگمنت', '470R', '0.25W', 42, 'AXIAL', 'یک عدد برای هر سگمنت؛ I≈1.5mA'),
    ('R_CL1,R_CL2', 'مقاومت LED کولن', '1k', '0.25W', 2, 'AXIAL', 'I≈2.8mA هر LED'),
    ('R_CB', 'مقاومت بیس Q1', '10k', '0.25W', 1, 'AXIAL', 'IB≈0.43mA؛ اشباع عمیق'),
    ('R_PU_SET..R_PU_MSTRST,R_POR', 'مقاومت بالاکش', '100k', '0.25W', 6, 'AXIAL', '۵ کلید + مدار POR'),
    ('R_S', 'مقاومت محدودکننده جریان کریستال', '220k', '0.25W', 1, 'AXIAL', 'Fig.13 دیتاشیت CD4060'),
    ('R_C', 'مقاومت بایاس اسیلاتور', '10M', '0.25W', 1, 'AXIAL', 'Fig.13 دیتاشیت CD4060'),
    ('C1,C2', 'خازن بار کریستال', '18pF', 'NP0', 2, 'RADIAL', 'CL=(18*18)/(36)+3.5=12.5pF'),
    ('C_BTN_SET..C_BTN_MSTRST', 'خازن دیبانس کلید', '1uF', 'X7R', 5, 'RADIAL', 'با 100k و اشمیت CD4093'),
    ('C_POR', 'خازن ریست روشن‌شدن', '10uF', '16V', 1, 'RADIAL', 'پالس ریست ≈0.87s'),
    ('D2', 'دیود تخلیه POR', '1N4148', '-', 1, 'DO-35', 'آند=POR_N، کاتد=VCC'),
    ('D1', 'دیود حفاظت پلاریته معکوس', '1N4007', '-', 1, 'DO-41', 'سری با ورودی تغذیه'),
    ('C_IN1', 'خازن ورودی رگولاتور', '0.33uF', 'film/ceramic', 1, 'RADIAL', 'مطابق دیتاشیت 7805'),
    ('C_IN2', 'خازن الکترولیت ورودی', '100uF', '25V', 1, 'RADIAL', 'نزدیک پایه ۱ U16'),
    ('C_OUT1', 'خازن خروجی رگولاتور', '100nF', 'ceramic', 1, 'RADIAL', 'پایدارسازی 7805'),
    ('C_OUT2', 'خازن الکترولیت خروجی', '100uF', '16V', 1, 'RADIAL', 'نزدیک پایه ۳ U16'),
    ('C_BULK', 'خازن ذخیره برد', '470uF', '16V', 1, 'RADIAL', 'جلوگیری از افت rail هنگام روشن‌شدن سگمنت‌ها'),
    ('C_BYP1..C_BYP15', 'خازن بای‌پس هر IC', '100nF', 'ceramic', 15, 'RADIAL', 'چسبیده به VDD/VSS هر IC منطقی'),
    ('SW_SET,SW_HOUR,SW_MIN,SW_SECRST,SW_MSTRST', 'کلید tact', 'SPST-NO', '6x6mm', 5, '4-pin', 'SET / HOUR+ / MIN+ / SEC RESET / MASTER RESET'),
    ('LED1,LED2', 'LED قرمز کولن', 'Vf≈2.0V', '5mm', 2, 'LED', 'چشمک‌زن ۱ هرتز'),
    ('J1', 'کانکتور تغذیه', '9-12V DC', '-', 1, '2-pin', 'جک DC یا ترمینال پیچی'),
]
with open(os.path.join(OUT, 'bom.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['ردیف/Ref', 'نام قطعه', 'مدل', 'مقدار', 'تعداد', 'پکیج', 'توضیحات'])
    for i, b in enumerate(bom, 1):
        w.writerow([i] + list(b))

# ---------------- markdown fragments ----------------
def md_table(headers, data):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|']
    for r in data:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)

ic_md = md_table(['Ref', 'مدل', 'مقدار', 'پکیج', 'پین', 'نام پین', 'نت', 'توضیح'], rows)
pa_md = md_table(['Ref', 'مدل', 'مقدار', 'پکیج', 'پین', 'نام پین', 'نت', 'توضیح'], prows)
bom_md = md_table(['#', 'Ref', 'نام قطعه', 'مدل', 'مقدار', 'تعداد', 'پکیج', 'توضیحات'],
                  [[i] + list(b) for i, b in enumerate(bom, 1)])
net_md = md_table(['نت', 'شرح'], [[k, netdesc[k]] for k in sorted(netdesc)])
for name, content in [('frag_ic_pins.md', ic_md), ('frag_passives.md', pa_md),
                      ('frag_bom.md', bom_md), ('frag_nets.md', net_md)]:
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        f.write(content + '\n')

# ---------------- sanity checks ----------------
allnets = set(r[6] for r in rows) | set(r[6] for r in prows)
unknown = allnets - set(netdesc) - {'NC'}
assert not unknown, unknown
# every non-NC net must appear at least twice (a connection needs >=2 pins)
from collections import Counter
cnt = Counter(r[6] for r in rows if r[6] != 'NC') + Counter(r[6] for r in prows if r[6] != 'NC')
singles = [n for n, c in cnt.items() if c < 2 and n not in ('NC',)]
assert not singles, singles
# no gate output net driven twice: count only true driver pins
drivers = {('U1', '3'), ('U2', '1'), ('U2', '13'), ('U3', '5'), ('U5', '5'), ('U7', '5')}
drivers |= {(u, str(p)) for u in ['U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15']
            for p in (3, 4, 10, 11)}
drv = Counter(r[6] for r in rows if (r[0], r[4]) in drivers and r[6] != 'NC')
multi = {n: c for n, c in drv.items() if c > 1}
assert not multi, multi
print('netlist rows:', len(rows), 'passive/display rows:', len(prows))
print('nets:', len(netdesc), 'BOM lines:', len(bom))
print('total component pins listed:', len(rows) + len(prows))
print('SANITY OK: no floating net, no double-driven gate output')