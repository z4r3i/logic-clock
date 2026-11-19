// Board renderer for the point-to-point build map. Coordinates are grid units (1 g = 1.27 mm).
const PW = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const DIGIT = ['#111', '#7a4b1f', '#d9480f', '#f76707', '#fab005', '#2b8a3e', '#1c7ed6', '#7048e8', '#868e96', '#f8f9fa'];
  const BANDS = { '470R': [4, 7, 1], '1k': [1, 0, 2], '10k': [1, 0, 3], '100k': [1, 0, 4], '220k': [2, 2, 4], '10M': [1, 0, 6] };
  const CODE = { '18pF': '18', '100nF': '104', '1uF': '105', '0.33uF': '334' };
  const RAILCOL = { VCC: '#e03131', GND: '#1864ab' };
  function el(tag, a, parent, text) {
    const e = document.createElementNS(NS, tag);
    for (const k in a) e.setAttribute(k, a[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function txt(g, x, y, s, size, fill, extra) {
    return el('text', Object.assign({ x, y, 'font-size': size, fill, 'text-anchor': 'middle', 'dominant-baseline': 'central' }, extra || {}), g, s);
  }
  function render(M, svg, o) {
    o = o || {};
    const X = x => (o.mirror ? M.W - x : x);
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    const root = el('g', {}, svg);
    el('rect', { x: -2, y: -2, width: M.W + 4, height: M.H + 4, rx: 2, fill: '#f6f1e4', stroke: '#c9b98f', 'stroke-width': 0.4 }, root);
    const L = {};
    ['rails', 'parts', 'wires', 'pins', 'labels', 'top'].forEach(k => (L[k] = el('g', { class: 'L-' + k }, root)));
    for (const r of M.rails) {
      const [x1, y1, x2, y2] = r.o === 'h' ? [X(r.s), r.f, X(r.e), r.f] : [X(r.f), r.s, X(r.f), r.e];
      const g = el('g', { class: 'rail', 'data-rail': r.name }, L.rails);
      el('line', { x1, y1, x2, y2, stroke: '#9aa0a6', 'stroke-width': 1.0, 'stroke-linecap': 'round' }, g);
      el('line', { x1, y1, x2, y2, stroke: RAILCOL[r.net], 'stroke-width': 0.3 }, g);
      if (r.o === 'h') txt(g, X(r.s) + (o.mirror ? 3.5 : -3.5), r.f, r.net === 'VCC' ? '+5V' : 'GND', 1.1, RAILCOL[r.net], { 'font-weight': 700 });
    }
    for (const p of M.parts) if (!(o.hideGhost && o.ghost && o.ghost(p))) drawPart(L, p, X, o);
    const hide = o.hideWire || (() => false), placed = [];
    for (const w of M.wires) {
      if (hide(w)) continue;
      const dim = !!(o.dim && o.dim(w));
      const g = el('g', { class: 'wire' + (dim ? ' dim' : ''), 'data-wire': w.id, 'data-net': w.net }, L.wires);
      const d = w.bridge ? bridgePath(w, X) : 'M' + w.pts.map(q => X(q[0]) + ' ' + q[1]).join(' L');
      const cw = o.thin ? 0.55 : 1.05, kw = o.thin ? 0.3 : 0.5;
      el('path', { d, fill: 'none', stroke: '#fff', 'stroke-width': cw, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', class: 'case' }, g);
      el('path', { d, fill: 'none', stroke: w.color, 'stroke-width': kw, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', class: 'core' }, g);
      if (o.wireLabels !== false) wireLabel(L.labels, w, X, placed, dim);
    }
    if (o.mirror) txt(L.top, M.W / 2, -0.2, 'نمای پشت (سمت لحیم) — آینه‌ای', 2.2, '#c92a2a', { 'font-weight': 700, opacity: 0.85 });
    for (const p of M.parts) if (!(o.hideGhost && o.ghost && o.ghost(p))) drawPins(L.pins, p, X, o);
    return { X, L };
  }
  function bridgePath(w, X) {
    const [a, b] = w.pts, mx = (X(a[0]) + X(b[0])) / 2, my = (a[1] + b[1]) / 2;
    return `M${X(a[0])} ${a[1]} Q${mx} ${my + w.bulge * 2.2} ${X(b[0])} ${b[1]}`;
  }
  function wireLabel(g, w, X, placed, dim) {
    const s = '#' + w.id, wd = 0.62 * s.length + 0.7, ht = 1.5;
    const cands = [];
    if (w.bridge) {
      const a = w.pts[0], b = w.pts[1];
      cands.push([(X(a[0]) + X(b[0])) / 2, (a[1] + b[1]) / 2 + w.bulge * 2.4]);
    } else {
      const segs = [];
      for (let i = 0; i + 1 < w.pts.length; i++) {
        const a = w.pts[i], b = w.pts[i + 1];
        segs.push({ a: [X(a[0]), a[1]], b: [X(b[0]), b[1]], len: Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) });
      }
      segs.sort((p, q) => q.len - p.len);
      for (const sg of segs) for (const t of [0.5, 0.3, 0.7, 0.15, 0.85])
        if (sg.len * Math.min(t, 1 - t) >= 1.2 || t === 0.5) cands.push([sg.a[0] + (sg.b[0] - sg.a[0]) * t, sg.a[1] + (sg.b[1] - sg.a[1]) * t]);
    }
    const hit = (x, y) => placed.some(r => Math.abs(r[0] - x) < (r[2] + wd) / 2 + 0.2 && Math.abs(r[1] - y) < ht + 0.2);
    const pos = cands.find(c => !hit(c[0], c[1])) || cands[0];
    placed.push([pos[0], pos[1], wd]);
    const lg = el('g', { class: 'wlabel' + (dim ? ' dim' : ''), 'data-wire': w.id }, g);
    el('rect', { x: pos[0] - wd / 2, y: pos[1] - ht / 2, width: wd, height: ht, rx: 0.7, fill: '#fff', stroke: w.color, 'stroke-width': 0.25 }, lg);
    txt(lg, pos[0], pos[1] + 0.05, s, 1.05, '#212529', { 'font-weight': 700, 'font-family': 'Consolas,monospace' });
  }
  function bodyBox(p, X) {
    const [x0, y0, x1, y1] = p.body, a = X(x0), b = X(x1);
    return { x: Math.min(a, b), y: y0, w: Math.abs(b - a), h: y1 - y0, cx: (a + b) / 2, cy: (y0 + y1) / 2 };
  }
  function drawPart(L, p, X, o) {
    const B = bodyBox(p, X), cls = 'part' + (o.ghost && o.ghost(p) ? ' ghost' : '');
    const g = el('g', { class: cls, 'data-ref': p.ref }, L.parts);
    const pin = n => p.pins[n], P = n => [X(pin(n).x), pin(n).y];
    const long = B.w >= B.h;
    const k = p.kind;
    if (k === 'DIP14' || k === 'DIP16') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: 0.35, fill: '#2b2f36', stroke: '#111', 'stroke-width': 0.15 }, g);
      const n = +k.slice(-2), a = P(1), z = P(n), half = P(n / 2);
      const ux = Math.sign(half[0] - a[0]), uy = Math.sign(half[1] - a[1]);
      const nx = ux ? (ux > 0 ? B.x : B.x + B.w) : (a[0] + z[0]) / 2, ny = uy ? (uy > 0 ? B.y : B.y + B.h) : (a[1] + z[1]) / 2;
      el('circle', { cx: nx, cy: ny, r: 0.75, fill: '#f6f1e4' }, g);
      el('circle', { cx: a[0] + (z[0] - a[0]) * 0.22 + ux * 0.9, cy: a[1] + (z[1] - a[1]) * 0.22 + uy * 0.9, r: 0.35, fill: '#dee2e6' }, g);
      txt(g, B.cx, B.cy - 0.7, p.ref, 1.6, '#fff', { 'font-weight': 700 });
      txt(g, B.cx, B.cy + 0.9, p.model.split('/')[0], 0.95, '#ced4da');
    } else if (k === 'DISP') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: 0.4, fill: '#25262b', stroke: '#111', 'stroke-width': 0.15 }, g);
      const sx = B.cx, sy = B.cy, w2 = 2.6, h2 = 4.6, sk = 0.5;
      el('path', { d: `M${sx - w2 + sk} ${sy - h2} h${2 * w2} l${-sk} ${h2} l${-sk} ${h2} h${-2 * w2} l${sk} ${-h2} z M${sx - w2 + sk / 2} ${sy} h${2 * w2}`, fill: 'none', stroke: '#5c1d1d', 'stroke-width': 0.8, 'stroke-linejoin': 'round' }, g);
      txt(g, B.cx, B.cy, p.ref, 1.5, '#fff', { 'font-weight': 700, stroke: '#25262b', 'stroke-width': 0.25, 'paint-order': 'stroke' });
    } else if (k === 'AX') {
      const a = P(1), b = P(2);
      el('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: '#868e96', 'stroke-width': 0.3 }, g);
      const isR = p.sub === 'res';
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: isR ? 0.6 : 0.3, fill: isR ? '#e9d8a6' : (p.sub === 'do35' ? '#f4a259' : '#212529'), stroke: '#555', 'stroke-width': 0.12 }, g);
      const vx = (b[0] - a[0]) / Math.hypot(b[0] - a[0], b[1] - a[1]), vy = (b[1] - a[1]) / Math.hypot(b[0] - a[0], b[1] - a[1]);
      const band = (t, col, wd) => {
        const cx = B.cx + vx * t, cy = B.cy + vy * t;
        el('rect', { x: cx - (vx ? wd / 2 : B.w / 2), y: cy - (vy ? wd / 2 : B.h / 2), width: vx ? wd : B.w, height: vy ? wd : B.h, fill: col }, g);
      };
      if (isR && BANDS[p.value]) {
        const bd = BANDS[p.value];
        [-1.6, -0.8, 0].forEach((t, i) => band(t, DIGIT[bd[i]], 0.45));
        band(1.4, '#c9a227', 0.45);
      } else if (!isR) band((long ? B.w : B.h) / 2 - 0.5, p.sub === 'do35' ? '#111' : '#ced4da', 0.5);
      const off = long ? [0, -B.h / 2 - 1.0] : [B.w / 2 + 0.3, 0];
      txt(g, B.cx + off[0], B.cy + off[1], p.ref.replace(/^R_/, ''), 0.95, '#343a40', long ? {} : { 'text-anchor': 'start', transform: `rotate(-90 ${B.cx + off[0] + 0.6} ${B.cy})`, x: B.cx + off[0] + 0.6 });
    } else if (k === 'CAP') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: Math.min(B.w, B.h) / 2, fill: p.value === '18pF' ? '#e8c37a' : '#d97b2b', stroke: '#8a4b12', 'stroke-width': 0.12 }, g);
      txt(g, B.cx, B.cy, CODE[p.value] || p.value, 0.85, '#fff', { 'font-weight': 700 });
      txt(g, B.cx, B.y - 0.8, p.ref.replace('C_BYP', 'CB'), 0.8, '#495057');
    } else if (k === 'ELEC' || k === 'LED') {
      const r = Math.min(B.w, B.h) / 2;
      el('circle', { cx: B.cx, cy: B.cy, r, fill: k === 'LED' ? '#ff8787' : '#2c3e6b', stroke: k === 'LED' ? '#c92a2a' : '#1b2a4a', 'stroke-width': 0.15 }, g);
      const m = P(2), sx = Math.sign(m[0] - B.cx);
      if (k === 'ELEC') {
        el('path', { d: `M${B.cx + sx * r * 0.55} ${B.cy - r * 0.83} A${r} ${r} 0 0 ${sx > 0 ? 1 : 0} ${B.cx + sx * r * 0.55} ${B.cy + r * 0.83}`, fill: '#ced4da' }, g);
        txt(g, B.cx - sx * r * 0.2, B.cy, p.value.replace('uF', 'µ'), 0.8, '#fff');
      } else el('line', { x1: B.cx + sx * r * 0.75, y1: B.cy - r * 0.66, x2: B.cx + sx * r * 0.75, y2: B.cy + r * 0.66, stroke: '#c92a2a', 'stroke-width': 0.3 }, g);
      const a = P(1); txt(g, a[0] - sx * 0.9, a[1] + 1.1, '+', 1.2, '#c92a2a', { 'font-weight': 700 });
      txt(g, B.cx, B.y - 0.8, p.ref, 0.85, '#495057');
    } else if (k === 'TO92') {
      el('path', { d: `M${B.x} ${B.y + B.h} L${B.x + B.w} ${B.y + B.h} A${B.w / 2} ${B.h} 0 0 0 ${B.x} ${B.y + B.h} z`, fill: '#212529' }, g);
      txt(g, B.cx, B.y + B.h * 0.62, '3904', 0.75, '#fff');
      txt(g, B.cx, B.y - 0.8, p.ref, 0.85, '#495057');
    } else if (k === 'TO220') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, fill: '#212529' }, g);
      el('rect', { x: B.x, y: B.y, width: B.w, height: 0.8, fill: '#adb5bd' }, g);
      txt(g, B.cx, B.cy + 0.4, '7805', 1.0, '#fff', { 'font-weight': 700 });
      txt(g, B.cx, B.y - 0.8, p.ref, 0.85, '#495057');
    } else if (k === 'XTAL') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: Math.min(B.w, B.h) / 2, fill: '#ced4da', stroke: '#868e96', 'stroke-width': 0.12 }, g);
      txt(g, B.cx + B.w / 2 + 2.6, B.cy, 'Y1 32.768k', 0.85, '#495057');
    } else if (k === 'TERM') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: 0.3, fill: '#2f9e44', stroke: '#1b5e20', 'stroke-width': 0.12 }, g);
      [1, 2].forEach(n => el('circle', { cx: P(n)[0], cy: B.cy, r: 1.0, fill: '#adb5bd', stroke: '#495057', 'stroke-width': 0.1 }, g));
      txt(g, B.cx, B.y - 0.8, 'J1  9-12V', 0.85, '#495057');
    } else if (k === 'TACT') {
      el('rect', { x: B.x, y: B.y, width: B.w, height: B.h, rx: 0.3, fill: '#343a40' }, g);
      el('circle', { cx: B.cx, cy: B.cy, r: Math.min(B.w, B.h) * 0.32, fill: '#868e96' }, g);
      txt(g, B.cx, B.y + B.h + 2.0, p.ref.replace('SW_', ''), 0.9, '#212529', { 'font-weight': 700 });
    }
  }
  function drawPins(g, p, X, o) {
    const B = bodyBox(p, X);
    for (const n in p.pins) {
      const q = p.pins[n], x = X(q.x), y = q.y;
      const nc = q.net === 'NC', joined = (M_joined[p.ref] || {})[n];
      const fill = nc ? '#fff' : q.net === 'VCC' ? '#e03131' : q.net === 'GND' ? '#1864ab' : '#495057';
      const pg = el('g', { class: 'pin', 'data-ref': p.ref, 'data-pin': n, 'data-net': q.net }, g);
      el('circle', { cx: x, cy: y, r: 0.45, fill: joined ? '#fff' : fill, stroke: nc || joined ? '#adb5bd' : '#212529', 'stroke-width': 0.12 }, pg);
      if (o.pinNums === false) continue;
      let dx = x - B.cx, dy = y - B.cy;
      if (p.kind.startsWith('DIP') || p.kind === 'DISP') { dx = 0; dy = Math.sign(dy); }
      const len = Math.hypot(dx, dy) || 1, t = 0.95;
      txt(pg, x + dx / len * t, y + dy / len * t, n, 0.7, nc ? '#adb5bd' : '#212529');
    }
  }
  let M_joined = {};
  return { render, el, txt, setJoined: j => { M_joined = j; }, RAILCOL };
})();
