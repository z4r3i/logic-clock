# -*- coding: utf-8 -*-
"""Assemble the self-contained HTML simulator: inject the tested engine + real
netlist pin data + net descriptions into the UI template."""
import csv, json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

eng = open(os.path.join(BASE, 'sim', 'clock_engine.js'), encoding='utf-8').read()

IC_MODELS = {'CD4060B','CD4013B','CD4026B','CD4081B','CD4071B','CD4093B','MC7805/LM7805','2N3904'}
pins = {}
with open(os.path.join(BASE, 'netlist', 'netlist.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['Model'] in IC_MODELS:
            e = pins.setdefault(r['Ref'], {'model': r['Model'], 'pkg': r['Package'], 'pins': []})
            e['pins'].append({'n': int(r['Pin']), 'name': r['PinName'], 'net': r['Net']})
for v in pins.values():
    v['pins'].sort(key=lambda p: p['n'])

netdesc = {}
with open(os.path.join(BASE, 'netlist', 'nets.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        netdesc[r['Net']] = r['Description']

tpl = open(os.path.join(BASE, 'visuals', 'sim_ui.html'), encoding='utf-8').read()
frag = (tpl.replace('{{ENGINE}}', eng)
           .replace('{{PIN_DATA}}', json.dumps(pins, ensure_ascii=False))
           .replace('{{NET_DESC}}', json.dumps(netdesc, ensure_ascii=False)))

# standalone full document (open directly in a browser)
standalone = ('<!DOCTYPE html>\n<html lang="fa" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
              '<title>شبیه‌ساز واقعی ساعت دیجیتال سخت‌افزاری</title>\n</head>\n'
              '<body style="margin:0;background:#0d1117">\n' + frag + '\n</body>\n</html>\n')
out = os.path.join(BASE, 'visuals', 'clock_simulator.html')
open(out, 'w', encoding='utf-8').write(standalone)
# fragment for in-conversation presentation
fragout = os.path.join(BASE, 'visuals', 'clock_simulator_frag.html')
open(fragout, 'w', encoding='utf-8').write(frag)
print('wrote', out, len(standalone), 'bytes (standalone);', len(frag), 'bytes (fragment);',
      len(pins), 'ICs;', len(netdesc), 'nets')