# -*- coding: utf-8 -*-
"""Builds visuals/schematic.html fragment from netlist.csv (single source of truth)."""
import csv, json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
NL = os.path.join(os.path.dirname(HERE), 'netlist', 'netlist.csv')

pins = []
with open(NL, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        pins.append([r['Ref'], r['Model'], r['Package'], r['Pin'], r['PinName'], r['Net'], r['Notes']])

blocks = [
    ('B1', 'تغذیه ۹–۱۲V → ۵V', ['U16', 'D1', 'J1', 'C_IN1', 'C_IN2', 'C_OUT1', 'C_OUT2', 'C_BULK'] + ['C_BYP%d' % i for i in range(1, 16)], (30, 20, 190, 80)),
    ('B2', 'ریست روشن‌شدن POR', ['R_POR', 'C_POR', 'D2', 'U15'], (30, 130, 190, 70)),
    ('B10', 'کلیدها + دیبانس', ['SW_SET', 'SW_HOUR', 'SW_MIN', 'SW_SECRST', 'SW_MSTRST', 'R_PU_SET', 'R_PU_HOUR', 'R_PU_MIN', 'R_PU_SECRST', 'R_PU_MSTRST', 'C_BTN_SET', 'C_BTN_HOUR', 'C_BTN_MIN', 'C_BTN_SECRST', 'C_BTN_MSTRST', 'U14', 'U15'], (30, 230, 190, 90)),
    ('B3', 'اسیلاتور + تقسیم ۲^۱۴', ['U1', 'Y1', 'C1', 'C2', 'R_C', 'R_S'], (270, 20, 210, 80)),
    ('B4', 'تقسیم بر ۲ → ۱Hz', ['U2', 'U15'], (530, 20, 180, 80)),
    ('B5', 'کنترل حالت SET', ['U2', 'U15', 'U11'], (530, 130, 180, 70)),
    ('B6', 'ثانیه MOD-60', ['U3', 'U4', 'U9'], (270, 240, 210, 80)),
    ('B7', 'دقیقه MOD-60', ['U5', 'U6', 'U9'], (270, 350, 210, 80)),
    ('B8', 'ساعت MOD-24', ['U7', 'U8', 'U10', 'U11'], (270, 460, 210, 80)),
    ('B9', 'مسیر کری/ریست + گیت کلاک', ['U12', 'U13', 'U11'], (530, 260, 180, 180)),
    ('B11', 'نمایشگرها + کولن', ['DS1', 'DS2', 'DS3', 'DS4', 'DS5', 'DS6', 'Q1', 'LED1', 'LED2', 'R_CB', 'R_CL1', 'R_CL2'] + ['R_%s%s' % (d, s) for d in ['HT', 'HU', 'MT', 'MU', 'ST', 'SU'] for s in 'ABCDEFG'], (760, 240, 210, 300)),
]
arrows = [
    ('B3', 'B4', 'CLK2HZ → U15/4 → CLK2HZ_INV'),
    ('B4', 'B9', 'CLK1HZ'),
    ('B2', 'B9', 'POR_RST'),
    ('B10', 'B5', 'BTN_SET'),
    ('B10', 'B9', 'BTN_SECRST / BTN_MSTRST'),
    ('B5', 'B9', 'SET_MODE / nSET_MODE / HOUR_GATE / MIN_GATE'),
    ('B9', 'B6', 'CLK_SEC / RST_SEC / RST_ST'),
    ('B6', 'B9', 'D6_ST'),
    ('B9', 'B7', 'CLK_MU / RST_MT / RST_GLOBAL'),
    ('B7', 'B9', 'D6_MT'),
    ('B9', 'B8', 'CLK_HU / RST_HOURS'),
    ('B8', 'B9', 'D24'),
    ('B9', 'B3', 'RST_GLOBAL'),
    ('B6', 'B11', 'SEG_SU / SEG_ST'),
    ('B7', 'B11', 'SEG_MU / SEG_MT'),
    ('B8', 'B11', 'SEG_HU / SEG_HT'),
    ('B4', 'B11', 'CLK1HZ → کولن'),
]

svg = ['<svg viewBox="0 0 1000 560" xmlns="http://www.w3.org/2000/svg" font-family="Tahoma,sans-serif">']
svg.append('<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="#555"/></marker></defs>')
pos = {b[0]: b[3] for b in blocks}
def center(bid):
    x, y, w, h = pos[bid]
    return x + w / 2, y + h / 2
for a, b, lab in arrows:
    x1, y1 = center(a); x2, y2 = center(b)
    dx, dy = x2 - x1, y2 - y1
    L = (dx * dx + dy * dy) ** .5
    ux, uy = dx / L, dy / L
    def edge(bid, ux, uy):
        x, y, w, h = pos[bid]
        cx, cy = x + w / 2, y + h / 2
        tx = (w / 2) / abs(ux) if ux else 1e9
        ty = (h / 2) / abs(uy) if uy else 1e9
        t = min(tx, ty)
        return cx + ux * t, cy + uy * t
    sx, sy = edge(a, ux, uy); ex, ey = edge(b, -ux, -uy)
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    svg.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#555" stroke-width="1.4" marker-end="url(#ar)"/>' % (sx, sy, ex, ey))
    svg.append('<text x="%.0f" y="%.0f" font-size="9" fill="#333" text-anchor="middle" transform="rotate(0)">%s</text>' % (mx, my - 4, lab))
for bid, title, refs, (x, y, w, h) in blocks:
    svg.append('<g class="blk" data-b="%s" style="cursor:pointer"><rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#eef9ee" stroke="#2c7a2c" stroke-width="1.6"/><text x="%d" y="%d" font-size="13" font-weight="bold" fill="#1a5c1a" text-anchor="middle">%s</text><text x="%d" y="%d" font-size="11" fill="#222" text-anchor="middle">%s</text><text x="%d" y="%d" font-size="9" fill="#666" text-anchor="middle">%s</text></g>' % (bid, x, y, w, h, x + w / 2, y + 22, bid, x + w / 2, y + 40, title, x + w / 2, y + 56, 'کلیک: پایه‌های قطعات'))
svg.append('</svg>')

data = {'pins': pins, 'blocks': [[b[0], b[1], b[2]] for b in blocks]}
html = """<style>
.clk-wrap{font-family:Tahoma,sans-serif;direction:rtl;color:#111}
.clk-wrap h2{font-size:18px;margin:6px 0}
.clk-wrap svg{width:100%;background:#fbfbf8;border:1px solid #ddd;border-radius:8px}
.clk-wrap .blk:hover rect{fill:#d8f0d8}
.clk-bar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;align-items:center}
.clk-bar select,.clk-bar input{padding:6px;font-family:inherit;font-size:13px}
.clk-chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.clk-chips button{padding:4px 9px;border:1px solid #2c7a2c;background:#fff;border-radius:12px;cursor:pointer;font-family:inherit;font-size:12px}
.clk-chips button.on{background:#2c7a2c;color:#fff}
.clk-wrap table{border-collapse:collapse;width:100%;font-size:12px;margin-top:6px}
.clk-wrap th,.clk-wrap td{border:1px solid #bbb;padding:4px 6px;text-align:right}
.clk-wrap th{background:#e8f9e8}
.clk-wrap td.net{font-family:Consolas,monospace;direction:ltr;text-align:left}
.clk-note{font-size:12px;color:#555;margin:6px 0}
</style>
<div class="clk-wrap">
<h2>شماتیک بلوکی تعاملی — ساعت دیجیتال سخت‌افزاری (۱۱ بلوک، ۴۸۴ پین)</h2>
<p class="clk-note">روی هر بلوک کلیک کنید تا قطعات آن لیست شود؛ روی هر قطعه کلیک کنید تا جدول کامل پین→نت آن باز شود. یا نام نت را جستجو کنید تا همهٔ پین‌های هم‌نت دیده شوند. داده مستقیماً از netlist.csv تولید شده است.</p>
__SVG__
<div class="clk-bar">
<label>بلوک: <select id="clk-bsel"></select></label>
<label>جستجوی نت: <input id="clk-net" placeholder="مثلا D6_ST یا RST_GLOBAL" size="24"></label>
</div>
<div class="clk-chips" id="clk-chips"></div>
<div id="clk-panel"></div>
</div>
<script>
(function(){
var DATA=__DATA__;
var pins=DATA.pins, blocks=DATA.blocks;
var bsel=document.getElementById('clk-bsel'), chips=document.getElementById('clk-chips'),
    panel=document.getElementById('clk-panel'), netin=document.getElementById('clk-net');
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function table(rows,head){
  var h='<table><tr>'+head.map(function(x){return '<th>'+esc(x)+'</th>';}).join('')+'</tr>';
  rows.forEach(function(r){h+='<tr>'+r.map(function(c,i){return '<td'+(head[i]==='نت'?' class="net"':'')+'>'+esc(c)+'</td>';}).join('')+'</tr>';});
  return h+'</table>';
}
function showRef(ref){
  var rows=pins.filter(function(p){return p[0]===ref;});
  panel.innerHTML='<h3 style="font-size:14px">'+esc(ref)+' — '+esc(rows[0]?rows[0][1]:'')+' ('+esc(rows[0]?rows[0][3]:'')+')</h3>'+
    table(rows.map(function(p){return [p[4],p[5],p[6],p[7]];}),['پین','نام پین','نت','توضیح']);
}
function showNet(q){
  q=q.trim();
  if(!q){panel.innerHTML='';return;}
  var rows=pins.filter(function(p){return p[6]===q||p[6].indexOf(q)===0;});
  panel.innerHTML='<h3 style="font-size:14px">نت‌های منطبق با «'+esc(q)+'»: '+rows.length+' پین</h3>'+
    table(rows.map(function(p){return [p[0],p[4],p[5],p[6]];}),['Ref','پین','نام پین','نت']);
}
function showBlock(bid){
  var b=blocks.filter(function(x){return x[0]===bid;})[0];
  chips.innerHTML='';
  b[2].forEach(function(ref){
    var btn=document.createElement('button'); btn.textContent=ref;
    btn.onclick=function(){chips.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});btn.classList.add('on');showRef(ref);};
    chips.appendChild(btn);
  });
  panel.innerHTML='<p class="clk-note">بلوک '+esc(b[0])+': '+esc(b[1])+' — یک قطعه را انتخاب کنید.</p>';
}
blocks.forEach(function(b){
  var o=document.createElement('option'); o.value=b[0]; o.textContent=b[0]+' — '+b[1]; bsel.appendChild(o);
});
bsel.onchange=function(){showBlock(bsel.value);};
netin.oninput=function(){showNet(netin.value);};
document.querySelectorAll('.blk').forEach(function(g){
  g.addEventListener('click',function(){bsel.value=g.getAttribute('data-b');showBlock(bsel.value);});
});
bsel.value='B6'; showBlock('B6');
})();
</script>
"""
html = html.replace('__SVG__', '\n'.join(svg)).replace('__DATA__', json.dumps(data, ensure_ascii=False))
standalone = ('<!DOCTYPE html>\n<html lang="fa" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
              '<title>شماتیک بلوکی و جدول پین‌ها — ساعت دیجیتال سخت‌افزاری</title>\n</head>\n'
              '<body style="margin:0;background:#fbfbf8">\n' + html + '\n</body>\n</html>\n')
out = os.path.join(HERE, 'schematic.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(standalone)
with open(os.path.join(HERE, 'schematic_frag.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print('wrote', out, len(standalone), 'bytes (standalone) + schematic_frag.html')