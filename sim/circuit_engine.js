(function (root) {
  'use strict';

  // Educational digital deltas, not SPICE, RC simulation, or physical delays.
  const F = 32768;
  const POR = 0.87;
  const SEG = Object.freeze({0:'abcdef', 1:'bc', 2:'abdeg', 3:'abcdg', 4:'bcfg',
    5:'acdfg', 6:'acdefg', 7:'abc', 8:'abcdefg', 9:'abcdfg'});
  const GATES = [[1, 2, 3], [5, 6, 4], [8, 9, 10], [12, 13, 11]];
  const FF = [{q:1, nq:2, clk:3, rst:4, d:5, set:6},
    {q:13, nq:12, clk:11, rst:10, d:9, set:8}];
  const DIV = [[7,4], [5,5], [4,6], [6,7], [14,8], [13,9], [15,10], [1,12], [2,13], [3,14]];
  const SEG_PINS = [[10,'a'], [12,'b'], [13,'c'], [9,'d'], [11,'e'], [6,'f'], [7,'g']];
  const DIGITS = ['U3', 'U4', 'U5', 'U6', 'U7', 'U8'];
  const BUTTONS = {SET:'تنظیم', HOUR:'ساعت', MIN:'دقیقه', SECRST:'صفرکردن ثانیه', MSTRST:'بازنشانی کلی'};
  const and = (a, b) => a === 0 || b === 0 ? 0 : a === 1 && b === 1 ? 1 : null;
  const or = (a, b) => a === 1 || b === 1 ? 1 : a === 0 && b === 0 ? 0 : null;
  const not = a => a === null ? null : 1 - a;

  function create(COMP) {
    if (!COMP || typeof COMP !== 'object') throw new TypeError('جدول قطعات و پایه‌ها لازم است.');
    const nets = {}, counts = {}, pins = {}, drivers = {}, sources = {}, devices = [], dividers = [], flips = [];
    const dirty = new Set();
    let powered = false, time = 0, timeError = 0, porPending = true;
    let frames = [], delta = 0, truncated = false, batchChanged = false;
    let reasons = [], held = {};

    for (const [ref, comp] of Object.entries(COMP)) {
      pins[ref] = {};
      for (const [pin, data] of Object.entries(comp.pins)) {
        const net = data[1];
        pins[ref][pin] = {key:ref + '.' + pin, net, output:null};
        nets[net] = null;
      }
    }
    for (const net of ['NC', 'GND', 'VCC', 'POR_N']) nets[net] = null;

    function driver(net, ref, pin) {
      const out = {net, ref, pin, value:null};
      if (net !== 'NC') (drivers[net] || (drivers[net] = [])).push(out);
      return out;
    }
    function source(net, ref) {
      nets[net] = null;
      return driver(net, ref, null);
    }
    function output(ref, pin) {
      const p = pins[ref][pin];
      if (!p) throw new Error('پایهٔ خروجی در جدول موجود نیست: ' + ref + '.' + pin);
      p.output = driver(p.net, ref, pin);
      return p.output;
    }
    function input(ref, pin) {
      const p = pins[ref] && pins[ref][pin];
      return !p || p.net === 'NC' ? null : nets[p.net];
    }
    function pinNet(ref, pin) {
      const p = pins[ref] && pins[ref][pin];
      return p && p.net !== 'NC' ? p.net : null;
    }
    function live(d) {
      return powered && input(d.ref, d.vdd) === 1 && input(d.ref, d.vss) === 0;
    }
    function write(out, value) {
      if (out.value === value) return false;
      out.value = value;
      batchChanged = true;
      if (out.net !== 'NC') dirty.add(out.net);
      return true;
    }
    function resolve() {
      const changes = [];
      for (const net of dirty) {
        const ds = drivers[net];
        const value = ds.every(d => d.value === ds[0].value) ? ds[0].value : null;
        if (nets[net] !== value) {
          changes.push({net, from:nets[net], to:value});
          nets[net] = value;
        }
      }
      dirty.clear();
      return changes;
    }
    function cause(title, ref, net) {
      if (frames.length < 511) reasons.push({title, ref, net});
    }
    function startBatch() { batchChanged = false; reasons = []; }

    sources.GND = source('GND', null);
    sources.VCC = source('VCC', null);
    sources.POR = source('POR_N', 'R_POR');
    for (const k of Object.keys(BUTTONS)) {
      const ref = 'SW_' + k;
      sources[k] = source(pinNet(ref, 1) || 'BTN_' + k + '_n', ref);
      held[k] = false;
    }

    for (const [ref, comp] of Object.entries(COMP)) {
      const match = /^CD(4081|4071|4093|4013|4026|4060)B?$/.exec(comp.model);
      if (!match) continue;
      const type = match[1];
      const d = {ref, type, vss:type === '4026' || type === '4060' ? 8 : 7,
        vdd:type === '4026' || type === '4060' ? 16 : 14};
      if (['4081', '4071', '4093'].includes(type)) {
        d.gates = GATES.map(([a,b,y]) => ({a, b, y, out:output(ref, y)}));
      } else if (type === '4013') {
        d.ff = FF.map(map => ({...map, value:0, prev:null, out:output(ref, map.q), inv:output(ref, map.nq)}));
        flips.push(d);
      } else if (type === '4026') {
        counts[ref] = 0;
        d.prev = null;
        d.segs = SEG_PINS.map(([pin,s]) => ({s, out:output(ref, pin)}));
        d.carry = output(ref, 5);
        d.enable = output(ref, 4);
        d.ungated = output(ref, 14);
      } else {
        d.count = 0;
        d.ticks = 0;
        d.origin = null;
        d.q = DIV.map(([pin,bit]) => ({bit, out:output(ref, pin)}));
        // Only connected taps need scheduled transitions; NC taps still expose their bits.
        d.quantum = Math.min(8192, ...d.q.filter(q => q.out.net !== 'NC').map(q => 2 ** (q.bit - 1)));
        output(ref, 9);
        output(ref, 10); // Oscillator pins stay unknown; there is no analog solver.
        dividers.push(d);
      }
      devices.push(d);
    }

    function pinValue(ref, pin) {
      const p = pins[ref] && pins[ref][String(pin)];
      if (!p) return null;
      return p.net === 'NC' ? (p.output ? p.output.value : null) : nets[p.net];
    }
    function snapshot() {
      const values = {};
      for (const pp of Object.values(pins)) {
        for (const p of Object.values(pp)) {
          values[p.key] = p.net === 'NC' ? (p.output ? p.output.value : null) : nets[p.net];
        }
      }
      return Object.freeze({time, nets:Object.freeze({...nets}), counts:Object.freeze({...counts}),
        divider:dividers.length ? dividers[0].count : 0, powered,
        setMode:powered && !!(flips[0] && flips[0].ff[1].value === 1), pinValues:Object.freeze(values)});
    }
    function record(title, ref, net, kind, changes, final = false) {
      const index = delta++;
      if (frames.length >= 511 && !final) { truncated = true; return; }
      frames.push(Object.freeze({...snapshot(), title, ref:ref || null, net:net || null, delta:index,
        kind, changes:Object.freeze(changes.map(c => Object.freeze({...c})))}));
    }
    function begin() {
      frames = [];
      delta = 0;
      truncated = false;
      record('آغاز تراکنش؛ دلتا ترتیب آموزشی است، نه تأخیر فیزیکی', null, null, 'initial', []);
    }
    function finish() {
      record(truncated ? 'پایان تراکنش؛ با سقف ۵۱۲ فریم، بخشی از مراحل میانی حذف شد' :
        'پایان تراکنش؛ حالت پایدار مدل دیجیتال', null, null, 'final', [], true);
      frames = Object.freeze(frames);
    }
    function commit(title, ref, net, kind = 'delta', force = false) {
      const changes = resolve();
      if (batchChanged || changes.length || force) {
        record(title, ref, net, kind, changes);
        return true;
      }
      return false;
    }
    function driveSources() {
      write(sources.GND, 0);
      write(sources.VCC, powered ? 1 : null);
      write(sources.POR, powered ? (porPending ? 0 : 1) : null);
      for (const k of Object.keys(BUTTONS)) write(sources[k], powered ? (held[k] ? 0 : 1) : null);
    }
    function driveDivider(d) {
      const enabled = live(d) && input(d.ref, 12) !== null;
      for (const q of d.q) write(q.out, enabled ? (d.count >> (q.bit - 1)) & 1 : null);
    }

    function evaluate(d, seed) {
      const on = live(d);
      if (d.gates) {
        for (const g of d.gates) {
          const a = input(d.ref, g.a), b = input(d.ref, g.b);
          const value = !on ? null : d.type === '4081' ? and(a, b) :
            d.type === '4071' ? or(a, b) : not(and(a, b));
          if (write(g.out, value)) cause('انتشار منطقی گیت ' + d.ref + '، پایهٔ ' + g.y,
            d.ref, pinNet(d.ref, g.y));
        }
      } else if (d.ff) {
        for (const ff of d.ff) {
          const clock = input(d.ref, ff.clk), reset = input(d.ref, ff.rst), set = input(d.ref, ff.set);
          let next = ff.value, why = 'انتشار خروجی فلیپ‌فلاپ';
          if (!seed && on) {
            if (reset === 1) { next = 0; why = 'بازنشانی ناهمگام با اولویت'; }
            else if (reset === null || set === null) { next = null; why = 'ورودی کنترلی نامعلوم'; }
            else if (set === 1) { next = 1; why = 'پیش‌نشانی ناهمگام'; }
            else if (ff.prev === 0 && clock === 1) { next = input(d.ref, ff.d); why = 'ثبت ورودی داده در لبهٔ بالارونده'; }
          }
          ff.prev = clock;
          ff.value = next;
          const changed = write(ff.out, on ? next : null);
          const invChanged = write(ff.inv, on ? not(next) : null);
          if (changed || invChanged) cause(why + '؛ ' + d.ref + '، پایهٔ ' + ff.q, d.ref,
            pinNet(d.ref, reset === 1 ? ff.rst : set === 1 ? ff.set : ff.clk));
        }
      } else if (d.type === '4026') {
        const clock = input(d.ref, 1), reset = input(d.ref, 15), inhibit = input(d.ref, 2);
        const old = counts[d.ref];
        let next = old, why = 'انتشار رقم، قطعات و خروجی انتقال';
        if (!seed && on) {
          if (reset === 1) { next = 0; why = 'صفرشدن ناهمگام شمارنده با اولویت بازنشانی'; }
          else if (reset === null) { next = null; why = 'ورودی بازنشانی نامعلوم'; }
          else if (d.prev === 0 && clock === 1 && inhibit !== 1) {
            next = inhibit === null || old === null ? null : (old + 1) % 10;
            why = 'شمارش ده‌دهی در لبهٔ بالاروندهٔ ساعت';
          }
        }
        d.prev = clock;
        counts[d.ref] = next;
        let changed = old !== next;
        const enable = on ? input(d.ref, 3) : null;
        changed = write(d.enable, enable) || changed;
        changed = write(d.carry, on && next !== null ? Number(next < 5) : null) || changed;
        changed = write(d.ungated, on && next !== null ? Number(next !== 2) : null) || changed;
        for (const seg of d.segs) {
          const bit = next === null ? null : Number(SEG[next].includes(seg.s));
          changed = write(seg.out, on ? and(enable, bit) : null) || changed;
        }
        if (changed) {
          batchChanged = true;
          cause(why + '؛ ' + d.ref, d.ref, pinNet(d.ref, reset === 1 ? 15 : 1));
        }
      } else {
        const reset = input(d.ref, 12);
        if (!seed) {
          if (!on || reset !== 0) {
            if (d.count !== 0) {
              batchChanged = true;
              cause('بازنشانی تقسیم‌کننده؛ ' + d.ref, d.ref, pinNet(d.ref, 12));
            }
            d.count = 0;
            d.ticks = 0;
            d.origin = null;
          } else if (d.origin === null) {
            d.origin = time;
            d.ticks = 0;
          }
        }
        const before = batchChanged;
        driveDivider(d);
        if (!before && batchChanged) cause('انتشار خروجی تقسیم‌کننده؛ ' + d.ref, d.ref, pinNet(d.ref, 3));
      }
    }
    function settle(seed = false) {
      for (let n = 0; n < 128; n++) {
        startBatch();
        // All devices sample the same net image; only this batch's commit publishes writes.
        for (const d of devices) evaluate(d, seed);
        const first = reasons[0];
        if (!commit(reasons.map(r => r.title).join('؛ ') || 'انتشار یک مرحلهٔ دلتا',
          first && first.ref, first && first.net)) return;
      }
      record('مدل پس از ۱۲۸ دلتا پایدار نشد؛ پایداری سخت‌افزار فرض نمی‌شود', null, null, 'unstable', []);
      throw new Error('مدار دیجیتال پس از ۱۲۸ دلتا پایدار نشد.');
    }

    function powerOn() {
      begin();
      powered = true;
      time = 0;
      timeError = 0;
      porPending = true;
      for (const k of Object.keys(held)) held[k] = false;
      for (const d of devices) {
        if (d.type === '4026') { counts[d.ref] = 0; d.prev = null; }
        if (d.ff) for (const ff of d.ff) { ff.value = 0; ff.prev = null; }
        if (d.type === '4060') { d.count = 0; d.ticks = 0; d.origin = null; }
      }
      startBatch();
      driveSources();
      commit('روشن‌شدن؛ ریل منطقی و بازنشانی آغازین ایده‌آل فعال شدند', null, 'VCC', 'power', true);
      settle();
      finish();
    }
    function powerOff() {
      begin();
      powered = false;
      startBatch();
      driveSources();
      for (const pp of Object.values(pins)) for (const p of Object.values(pp)) if (p.output) write(p.output, null);
      for (const d of dividers) d.origin = null;
      commit('خاموش‌شدن؛ جز زمین همهٔ پایه‌ها نامعلوم‌اند و زمان مدل متوقف است', null, 'VCC', 'power', true);
      finish();
    }

    function tolerance(t) { return 8 * Number.EPSILON * Math.max(1, Math.abs(t)); }
    function nextBoundary(q14Only = false) {
      let next = porPending ? POR : Infinity;
      for (const d of dividers) {
        if (d.origin === null) continue;
        const quantum = q14Only ? 8192 : d.quantum;
        next = Math.min(next, d.origin + (d.ticks + quantum - d.ticks % quantum) / F);
      }
      return next;
    }
    function runUntil(target) {
      while (time < target) {
        const boundary = nextBoundary();
        if (Math.abs(target - boundary) <= tolerance(target)) target = boundary;
        time = Math.min(target, boundary);
        startBatch();
        for (const d of dividers) {
          if (d.origin === null) continue;
          const exact = (time - d.origin) * F;
          const nearest = Math.round(exact);
          const ticks = Math.abs(exact - nearest) <= tolerance(time) * F ? nearest : Math.floor(exact);
          if (ticks === d.ticks) continue;
          d.ticks = ticks;
          d.count = ticks % 16384;
          batchChanged = true;
          driveDivider(d);
          cause('پیشروی چرخه‌های بلور ایده‌آل و انتشار بیت‌های تقسیم‌کننده؛ ' + d.ref,
            d.ref, pinNet(d.ref, 3));
        }
        const first = reasons[0];
        commit(first ? first.title : 'پیشروی زمان مدل', first && first.ref, first && first.net, 'divider');
        if (porPending && time >= POR) {
          porPending = false;
          startBatch();
          driveSources();
          commit('پایان بازنشانی آغازین در ۰٫۸۷ ثانیه؛ مرز زمانی ایده‌آل، نه مدل آرسی', 'R_POR', 'POR_N', 'por');
        }
        settle();
      }
    }
    function advance(dt) {
      if (typeof dt !== 'number' || !Number.isFinite(dt) || dt < 0) throw new RangeError('گام زمان باید عدد متناهی و نامنفی باشد.');
      const adjusted = dt - timeError;
      const target = time + adjusted;
      if (!Number.isFinite(target) || target * F > Number.MAX_SAFE_INTEGER) throw new RangeError('زمان از محدودهٔ دقیق مدل خارج است.');
      begin();
      if (powered && dt > 0) {
        timeError = (target - time) - adjusted;
        runUntil(target);
      }
      finish();
    }
    function nextEdge() {
      const next = nextBoundary(true);
      if (!powered || !Number.isFinite(next)) {
        begin();
        record('تقسیم‌کننده خاموش یا در بازنشانی نگه داشته شده است؛ لبه‌ای در انتظار نیست', null, null, 'held', []);
        finish();
      } else {
        timeError = 0;
        advance(Math.max(0, next - time));
      }
    }
    function crystalStep() { advance(1 / F); }
    function button(k, down) {
      if (!Object.prototype.hasOwnProperty.call(BUTTONS, k)) throw new RangeError('کلید ناشناخته است.');
      begin();
      const changed = held[k] !== down;
      held[k] = down;
      startBatch();
      driveSources();
      commit((changed ? (down ? 'فشردن' : 'رهاکردن') : 'بدون لبهٔ تازه برای') + ' کلید ' + BUTTONS[k] +
        '؛ ورودی کلید بدون جهش و ایده‌آل است', sources[k].ref, sources[k].net, 'button', true);
      if (powered) settle();
      finish();
    }
    function loadScenario(h, m, s) {
      if (![h,m,s].every(Number.isInteger) || h < 0 || h > 23 || m < 0 || m > 59 || s < 0 || s > 59) {
        throw new RangeError('پیش‌تنظیم باید ساعت ۰ تا ۲۳ و دقیقه و ثانیهٔ ۰ تا ۵۹ باشد.');
      }
      begin();
      powered = true;
      time = 0;
      timeError = 0;
      porPending = false;
      for (const k of Object.keys(held)) held[k] = false;
      const values = [s % 10, Math.floor(s / 10), m % 10, Math.floor(m / 10), h % 10, Math.floor(h / 10)];
      for (const d of devices) {
        if (d.type === '4026') counts[d.ref] = DIGITS.includes(d.ref) ? values[DIGITS.indexOf(d.ref)] : 0;
        if (d.ff) for (const ff of d.ff) ff.value = 0;
        if (d.type === '4060') { d.count = 0; d.ticks = 0; d.origin = 0; }
      }
      startBatch();
      driveSources();
      commit('پیش‌تنظیم مجازی آموزشی؛ سخت‌افزار پایهٔ بارگذاری ندارد و فلیپ‌فلاپ اول صفر است', null, null, 'preset', true);
      settle(true);
      // Seed edge history only after the whole combinational graph has settled.
      for (const d of devices) {
        if (d.type === '4026') d.prev = input(d.ref, 1);
        if (d.ff) for (const ff of d.ff) ff.prev = input(d.ref, ff.clk);
        if (d.type === '4060' && input(d.ref, 12) !== 0) d.origin = null;
      }
      settle();
      finish();
    }
    function display() {
      const pair = (tens, units) => counts[tens] == null || counts[units] == null ? '--' :
        String(counts[tens] * 10 + counts[units]).padStart(2, '0');
      return pair('U8','U7') + ':' + pair('U6','U5') + ':' + pair('U4','U3');
    }

    const engine = {nets, counts, display, pinValue, snapshot, advance, nextEdge, crystalStep,
      press:k => button(k, true), release:k => button(k, false), powerOn, powerOff, loadScenario,
      get divider() { return dividers.length ? dividers[0].count : 0; },
      get time() { return time; }, get powered() { return powered; },
      get setMode() { return powered && !!(flips[0] && flips[0].ff[1].value === 1); },
      get frames() { return frames; }};
    startBatch();
    driveSources();
    resolve();
    powerOn();
    return engine;
  }

  const api = Object.freeze({create, F, SEG});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CircuitEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
