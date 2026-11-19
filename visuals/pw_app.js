// Interactive build map: overview + step-by-step build mode, top/back (mirrored) view, pan/zoom.
(function () {
  const M = window.PW_MODEL, $ = id => document.getElementById(id);
  const svg = $('pw-svg'), panel = $('pw-panel');
  const parts = Object.fromEntries(M.parts.map(p => [p.ref, p]));
  const wires = Object.fromEntries(M.wires.map(w => [w.id, w]));
  const joined = {};
  M.joined.forEach(j => ((joined[j.ref] = joined[j.ref] || {})[j.pin] = j.to));
  PW.setJoined(joined);
  const stepOfWire = {}, stepOfPart = {};
  M.steps.forEach((s, i) => { if (s.t === 'wire') stepOfWire[s.id] = i; if (s.t === 'part') stepOfPart[s.ref] = i; });
  const KEY = 'pw-done-v1';
  let done = new Set(JSON.parse(localStorage.getItem(KEY) || '[]'));
  let S = { mode: 'build', mirror: false, step: +(localStorage.getItem('pw-step') || 0), phase: -1, sel: null };
  let vb = { x: -4, y: -4, w: M.W + 8, h: M.H + 8 };
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const fa = n => String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
  const mm = g => Math.round(g * M.G);
  const RAILNAME = M.railNames;
  const pinTxt = (e) => e ? `<b>${esc(e.ref)}</b> پایهٔ <b>${e.pin}</b> <span class="dim">(${esc(parts[e.ref].pins[e.pin].name)})</span>` : '';

  const mini = $('pw-mini');
  function drawMini(hl) {
    mini.setAttribute('viewBox', `-3 -3 ${M.W + 6} ${M.H + 6}`);
    while (mini.firstChild) mini.removeChild(mini.firstChild);
    for (const r of M.rails) {
      const [x1, y1, x2, y2] = r.o === 'h' ? [X(r.s), r.f, X(r.e), r.f] : [X(r.f), r.s, X(r.f), r.e];
      PW.el('line', { x1, y1, x2, y2, stroke: PW.RAILCOL[r.net], 'stroke-width': 0.8, opacity: 0.5 }, mini);
    }
    for (const p of M.parts) {
      const b = p.body, a = X(b[0]), c = X(b[2]);
      PW.el('rect', { x: Math.min(a, c), y: b[1], width: Math.abs(c - a), height: b[3] - b[1], fill: p.kind.startsWith('DIP') || p.kind === 'DISP' ? '#495057' : '#adb5bd' }, mini);
    }
    if (hl) PW.el('rect', { x: hl[0] - 2, y: hl[1] - 2, width: hl[2] - hl[0] + 4, height: hl[3] - hl[1] + 4, fill: '#ffd43b', opacity: 0.7, stroke: '#e8590c', 'stroke-width': 0.8 }, mini);
    PW.el('rect', { id: 'mini-view', fill: 'none', stroke: '#e8590c', 'stroke-width': 1.2 }, mini);
    setVB();
  }
  mini.addEventListener('click', e => {
    const r = mini.getBoundingClientRect(), x = -3 + (e.clientX - r.left) / r.width * (M.W + 6), y = -3 + (e.clientY - r.top) / r.height * (M.H + 6);
    vb = { ...vb, x: x - vb.w / 2, y: y - vb.h / 2 }; setVB();
  });
  function setVB() {
    svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    const v = document.getElementById('mini-view');
    if (v) { v.setAttribute('x', vb.x); v.setAttribute('y', vb.y); v.setAttribute('width', vb.w); v.setAttribute('height', vb.h); }
  }
  function fit(b, minW) {
    const r = svg.getBoundingClientRect(), ar = r.width / Math.max(1, r.height);
    let w = Math.max(b[2] - b[0] + 16, minW || 0), h = Math.max(b[3] - b[1] + 12, w / ar);
    w = Math.max(w, h * ar);
    vb = { x: (b[0] + b[2]) / 2 - w / 2, y: (b[1] + b[3]) / 2 - h / 2, w, h }; setVB();
  }
  const X = x => (S.mirror ? M.W - x : x);
  function bbOf(st) {
    if (st.t === 'wire') { const w = wires[st.id]; const xs = w.pts.map(q => X(q[0])), ys = w.pts.map(q => q[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; }
    if (st.t === 'part') { const b = parts[st.ref].body, a = X(b[0]), c = X(b[2]); return [Math.min(a, c), b[1], Math.max(a, c), b[3]]; }
    if (st.t === 'rail') { const r = M.rails.find(r => r.name === st.rail); return r.o === 'h' ? [Math.min(X(r.s), X(r.e)), r.f, Math.max(X(r.s), X(r.e)), r.f] : [X(r.f), r.s, X(r.f), r.e]; }
    const refs = M.phases[st.ph].parts.map(r => parts[r].body);
    return [Math.min(...refs.map(b => Math.min(X(b[0]), X(b[2])))), Math.min(...refs.map(b => b[1])), Math.max(...refs.map(b => Math.max(X(b[0]), X(b[2])))), Math.max(...refs.map(b => b[3]))];
  }

  function draw() {
    const st = M.steps[S.step], build = S.mode === 'build';
    const o = { mirror: S.mirror, wireLabels: build, thin: !build };
    if (build) {
      o.ghost = p => stepOfPart[p.ref] > S.step;
      o.hideWire = w => stepOfWire[w.id] > S.step;
      o.dim = w => stepOfWire[w.id] < S.step;
    } else if (S.phase >= 0) {
      o.ghost = p => p.phase !== S.phase;
      o.hideWire = w => w.phase !== S.phase;
    }
    const { L } = PW.render(M, svg, o);
    svg.classList.toggle('building', build);
    const top = L.top;
    const mark = (x, y, label, col, below) => {
      PW.el('circle', { cx: x, cy: y, r: 1.5, fill: 'none', stroke: col, 'stroke-width': 0.45, class: 'pulse' }, top);
      if (!label) return;
      const w = 0.62 * label.length + 1.2, ty = y + (below ? 3.2 : -3.2);
      PW.el('rect', { x: x - w / 2, y: ty - 1.0, width: w, height: 2.0, rx: 0.5, fill: col }, top);
      PW.txt(top, x, ty, label, 1.25, '#fff', { 'font-weight': 700, 'font-family': 'Consolas,monospace' });
    };
    const hlWire = id => {
      const g = svg.querySelector(`.L-wires [data-wire="${id}"]`); if (!g) return;
      const glow = g.querySelector('.case').cloneNode(); glow.setAttribute('stroke', '#ffd43b'); glow.setAttribute('stroke-width', 2.6); glow.setAttribute('opacity', 0.8);
      g.insertBefore(glow, g.firstChild); g.querySelector('.core').setAttribute('stroke-width', 0.85); g.classList.remove('dim');
      const w = wires[id], a = w.pts[0], b = w.pts[w.pts.length - 1];
      if (!build) PW.txt(top, X(a[0]), a[1] - 2.4, '#' + w.id, 1.5, w.color, { 'font-weight': 800, stroke: '#fff', 'stroke-width': 0.4, 'paint-order': 'stroke' });
      mark(X(a[0]), a[1], `${w.a.ref}.${w.a.pin}`, '#e8590c', a[1] > b[1]);
      mark(X(b[0]), b[1], w.b ? `${w.b.ref}.${w.b.pin}` : (w.net === 'VCC' ? '+5V' : 'GND'), '#1971c2', b[1] >= a[1]);
    };
    const hlPart = ref => {
      const b = parts[ref].body, a = X(b[0]), c = X(b[2]);
      PW.el('rect', { x: Math.min(a, c) - 1.2, y: b[1] - 1.2, width: Math.abs(c - a) + 2.4, height: b[3] - b[1] + 2.4, rx: 0.8, fill: 'none', stroke: '#e8590c', 'stroke-width': 0.4, 'stroke-dasharray': '1 0.6', class: 'pulse' }, top);
    };
    if (build) {
      if (st.t === 'wire') hlWire(st.id);
      if (st.t === 'part') hlPart(st.ref);
      if (st.t === 'rail') { const g = svg.querySelector(`[data-rail="${st.rail}"] line`); if (g) { const c = g.cloneNode(); c.setAttribute('stroke', '#ffd43b'); c.setAttribute('stroke-width', 2.4); c.setAttribute('opacity', .8); g.parentNode.insertBefore(c, g); } }
    } else if (S.sel) {
      if (S.sel.t === 'wire') hlWire(S.sel.id); else hlPart(S.sel.ref);
    }
    drawMini(build ? bbOf(st) : S.sel ? bbOf(S.sel) : null);
    renderPanel();
  }

  function stepHTML(st, i) {
    const n = `<span class="sn">مرحلهٔ ${fa(i + 1)} از ${fa(M.steps.length)}</span>`;
    if (st.t === 'rail') {
      const r = M.rails.find(r => r.name === st.rail);
      return `${n}<h2>ریل ${r.net === 'VCC' ? '+5V' : 'GND'}: ${esc(RAILNAME[r.name])}</h2><p>یک سیم مسی <b>لخت</b> (بدون لاک) به طول حدود <b>${fa(mm(r.e - r.s) + 10)} میلی‌متر</b> مثل خط ${r.net === 'VCC' ? 'قرمز' : 'آبی'} روی نقشه بکش و محکم کن.</p><p class="warn">ریل‌های +5V و GND هرگز نباید به هم برسند. سیم‌های لاکی بعداً می‌توانند از رویشان رد شوند.</p>`;
    }
    if (st.t === 'part') {
      const p = parts[st.ref];
      let h = `${n}<h2>${esc(p.ref)} — ${esc(p.model)} ${p.value && p.value !== '-' ? esc(p.value) : ''}</h2><p>${esc(M.hints[p.ref] || '')}</p>`;
      if (st.direct.length) h += '<ul>' + st.direct.map(d => `<li>پایهٔ <b>${d.pin}</b> را مستقیم روی <b>ریل ${esc(RAILNAME[d.rail])}</b> لحیم کن (بدون سیم).</li>`).join('') + '</ul>';
      const j = joined[p.ref]; if (j) h += `<p class="dim">پایه‌های ${Object.keys(j).map(k => `${k}↔${j[k]}`).join('، ')} داخل قطعه به هم وصل‌اند؛ سیم نمی‌خواهند.</p>`;
      return h;
    }
    if (st.t === 'wire') {
      const w = wires[st.id], cut = Math.ceil((mm(w.len) + 15) / 5) * 5;
      const to = w.b ? pinTxt(w.b) : `<b>ریل ${esc(RAILNAME[w.rail])}</b>`;
      return `${n}<h2 style="color:${w.color}">سیم #${w.id}${w.bridge ? ' (پل کوتاه)' : ''}</h2><p class="ft">از: ${pinTxt(w.a)}</p><p class="ft">به: ${to}</p><p>نت: <code>${esc(w.net)}</code> · طول تقریبی برش: <b>${fa(cut)} mm</b></p><p class="dim">دو سر سیم لاکی را با هویه/سنباده لاک‌برداری کن، فقط سرها را لحیم کن؛ بدنهٔ سیم عایق است و می‌تواند از روی سیم‌های دیگر رد شود.</p>`;
    }
    return `${n}<h2>آزمایش پایان «${esc(M.phases[st.ph].title)}»</h2><p>${esc(st.text)}</p>`;
  }
  function renderPanel() {
    const build = S.mode === 'build';
    let h = '';
    if (build) {
      const st = M.steps[S.step], ph = st.ph, inPh = M.steps.map((s, i) => [s, i]).filter(([s]) => s.ph === ph);
      h += `<div class="prog"><div style="width:${100 * done.size / M.steps.length}%"></div></div><div class="dim">انجام‌شده: ${fa(done.size)} از ${fa(M.steps.length)} · بخش ${fa(ph + 1)} از ${fa(M.phases.length)}: <b>${esc(M.phases[ph].title)}</b></div>`;
      h += `<div class="card">${stepHTML(st, S.step)}</div><div class="btns"><button id="b-prev">› قبلی</button><button id="b-done" class="pri">${done.has(S.step) ? '✓ انجام شده' : '✓ انجام شد، بعدی'}</button><button id="b-next">بعدی ‹</button></div>`;
      h += '<div class="list">' + inPh.map(([s, i]) => `<div class="li${i === S.step ? ' cur' : ''}${done.has(i) ? ' ok' : ''}" data-i="${i}">${done.has(i) ? '✓' : '○'} ${s.t === 'wire' ? 'سیم #' + s.id + ': ' + esc(wires[s.id].a.ref) + '.' + wires[s.id].a.pin + ' → ' + (wires[s.id].b ? esc(wires[s.id].b.ref) + '.' + wires[s.id].b.pin : 'ریل') : s.t === 'part' ? 'نصب ' + esc(s.ref) : s.t === 'rail' ? 'ریل ' + esc(s.rail) : 'آزمایش'}</div>`).join('') + '</div>';
    } else {
      h += `<p>کل نقشه: ${fa(M.parts.length)} قطعه، ${fa(M.wires.length)} سیم لاکی، ${fa(M.rails.length)} ریل لخت. هیچ دو سیمی روی هم نیستند؛ فقط به‌صورت عمود از روی هم رد می‌شوند.</p><label>نمایش بخش: <select id="ph-sel"><option value="-1">همه</option>${M.phases.map((p, i) => `<option value="${i}"${S.phase === i ? ' selected' : ''}>${fa(i + 1)}. ${esc(p.title)}</option>`).join('')}</select></label>`;
      if (S.sel && S.sel.t === 'wire') { const w = wires[S.sel.id]; h += `<div class="card"><h2 style="color:${w.color}">سیم #${w.id}</h2><p class="ft">از: ${pinTxt(w.a)}</p><p class="ft">به: ${w.b ? pinTxt(w.b) : 'ریل ' + esc(RAILNAME[w.rail])}</p><button id="b-go" data-i="${stepOfWire[w.id]}">رفتن به این مرحله در حالت ساخت</button></div>`; }
      if (S.sel && S.sel.t === 'part') { const p = parts[S.sel.ref]; h += `<div class="card"><h2>${esc(p.ref)} — ${esc(p.model)}</h2><p>${esc(M.hints[p.ref] || '')}</p><table>${Object.keys(p.pins).map(k => `<tr><td>${k}</td><td>${esc(p.pins[k].name)}</td><td><code>${esc(p.pins[k].net)}</code></td></tr>`).join('')}</table></div>`; }
    }
    panel.innerHTML = h;
    const on = (id, f) => { const e = $(id); if (e) e.onclick = f; };
    on('b-prev', () => go(S.step - 1)); on('b-next', () => go(S.step + 1));
    on('b-done', () => { done.add(S.step); save(); go(S.step + 1); });
    on('b-go', e => { S.mode = 'build'; go(+e.target.dataset.i); syncBar(); });
    const sel = $('ph-sel'); if (sel) sel.onchange = () => { S.phase = +sel.value; S.sel = null; draw(); };
    panel.querySelectorAll('.li').forEach(e => (e.onclick = () => go(+e.dataset.i)));
    const cur = panel.querySelector('.li.cur'); if (cur) cur.scrollIntoView({ block: 'nearest' });
  }
  function save() { localStorage.setItem(KEY, JSON.stringify([...done])); localStorage.setItem('pw-step', S.step); }
  function go(i) {
    S.step = Math.max(0, Math.min(M.steps.length - 1, i)); save(); draw();
    const t = M.steps[S.step].t;
    fit(bbOf(M.steps[S.step]), t === 'wire' ? 64 : t === 'part' ? 56 : 80);
  }
  function syncBar() {
    $('m-build').classList.toggle('on', S.mode === 'build'); $('m-over').classList.toggle('on', S.mode === 'over');
    $('v-top').classList.toggle('on', !S.mirror); $('v-back').classList.toggle('on', S.mirror);
  }
  $('m-build').onclick = () => { S.mode = 'build'; syncBar(); go(S.step); };
  $('m-over').onclick = () => { S.mode = 'over'; S.sel = null; syncBar(); draw(); fit([0, 0, M.W, M.H]); };
  $('v-top').onclick = () => { S.mirror = false; syncBar(); draw(); };
  $('v-back').onclick = () => { S.mirror = true; syncBar(); draw(); };
  $('z-fit').onclick = () => fit([0, 0, M.W, M.H]);
  const zoom = (k, cx, cy) => { cx = cx ?? vb.x + vb.w / 2; cy = cy ?? vb.y + vb.h / 2; vb = { x: cx - (cx - vb.x) * k, y: cy - (cy - vb.y) * k, w: vb.w * k, h: vb.h * k }; setVB(); };
  $('z-in').onclick = () => zoom(0.75); $('z-out').onclick = () => zoom(1.33);
  $('b-reset').onclick = () => { if (confirm('همهٔ تیک‌های «انجام شد» پاک شود؟')) { done = new Set(); save(); draw(); } };
  const toSvg = e => { const r = svg.getBoundingClientRect(); return [vb.x + (e.clientX - r.left) / r.width * vb.w, vb.y + (e.clientY - r.top) / r.height * vb.h]; };
  svg.addEventListener('wheel', e => { e.preventDefault(); const [x, y] = toSvg(e); zoom(e.deltaY > 0 ? 1.15 : 0.87, x, y); }, { passive: false });
  let drag = null;
  svg.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, vb: { ...vb }, moved: false }; svg.setPointerCapture(e.pointerId); });
  svg.addEventListener('pointermove', e => {
    if (!drag) return; const r = svg.getBoundingClientRect(), dx = (e.clientX - drag.x) / r.width * vb.w, dy = (e.clientY - drag.y) / r.height * vb.h;
    if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 4) drag.moved = true;
    vb = { ...drag.vb, x: drag.vb.x - dx, y: drag.vb.y - dy }; setVB();
  });
  svg.addEventListener('pointerup', e => {
    const d = drag; drag = null; if (!d || d.moved) return;
    const t = document.elementFromPoint(e.clientX, e.clientY);
    const w = t && t.closest('[data-wire]'), p = t && t.closest('[data-ref]');
    if (S.mode === 'build') { if (w) go(stepOfWire[w.dataset.wire]); else if (p && stepOfPart[p.dataset.ref] != null) go(stepOfPart[p.dataset.ref]); return; }
    S.sel = w ? { t: 'wire', id: +w.dataset.wire } : p ? { t: 'part', ref: p.dataset.ref } : null; draw();
  });
  document.addEventListener('keydown', e => {
    if (S.mode !== 'build' || e.target.tagName === 'SELECT') return;
    if (e.key === 'ArrowLeft' || e.key === 'PageDown') go(S.step + 1);
    if (e.key === 'ArrowRight' || e.key === 'PageUp') go(S.step - 1);
    if (e.key === ' ') { e.preventDefault(); done.add(S.step); save(); go(S.step + 1); }
  });
  window.__pw = { go, S, M, draw, fit, setMode: m => $(m === 'build' ? 'm-build' : 'm-over').click(), mirror: v => $(v ? 'v-back' : 'v-top').click() };
  syncBar(); go(S.step);
})();
