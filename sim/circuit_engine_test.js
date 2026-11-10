'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {create, F, SEG} = require('./circuit_engine');

function parseCSV(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  text = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (c === ',' && !quoted) { row.push(field); field = ''; }
    else if ((c === '\n' || c === '\r') && !quoted) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      if (row.some(Boolean)) rows.push(row);
      row = []; field = '';
    } else field += c;
  }
  if (quoted) throw new Error('Unterminated CSV field');
  if (field || row.length) { row.push(field); rows.push(row); }
  const header = rows.shift();
  return rows.map(r => Object.fromEntries(header.map((name, i) => [name, r[i] || ''])));
}

const COMP = {};
for (const r of parseCSV(fs.readFileSync(path.join(__dirname, '..', 'netlist', 'netlist.csv'), 'utf8'))) {
  if (!COMP[r.Ref]) COMP[r.Ref] = {model:r.Model, value:r.Value, pkg:r.Package, pins:{}};
  COMP[r.Ref].pins[r.Pin] = [r.PinName, r.Net, r.Notes];
}
const clone = () => JSON.parse(JSON.stringify(COMP));
const fresh = () => create(COMP);
const tap = (e, k) => { e.press(k); e.release(k); };
const near = (a, b, epsilon = 1e-10) => assert.ok(Math.abs(a - b) < epsilon, `${a} != ${b}`);
const analog = [...new Set(Object.values(COMP).flatMap(c => Object.values(c.pins).map(p => p[1])))]
  .filter(n => /^(VIN2?$|XTAL_|OSC_FB$|DSP_|COLON_)/.test(n));
const pinKeys = Object.entries(COMP).flatMap(([ref,c]) => Object.keys(c.pins).map(p => ref + '.' + p));
let passed = 0;

function test(name, fn) {
  fn();
  passed++;
  console.log('PASS ' + name);
}
function sameState(a, b) {
  near(a.time, b.time);
  assert.deepEqual(a.nets, b.nets);
  assert.deepEqual(a.counts, b.counts);
  assert.equal(a.divider, b.divider);
  assert.equal(a.powered, b.powered);
  assert.equal(a.setMode, b.setMode);
  assert.deepEqual(a.snapshot().pinValues, b.snapshot().pinValues);
}
function assertFrames(e) {
  assert.ok(e.frames.length >= 2 && e.frames.length <= 512);
  assert.equal(e.frames[0].kind, 'initial');
  assert.equal(e.frames.at(-1).kind, 'final');
  const last = e.frames.at(-1);
  const {title, ref, net, delta, changes, kind, ...state} = last;
  assert.deepEqual(state, e.snapshot());
  let prev = -1;
  for (let i = 0; i < e.frames.length; i++) {
    const f = e.frames[i];
    assert.ok(Number.isInteger(f.delta) && f.delta > prev);
    assert.match(f.title, /[\u0600-\u06ff]/);
    assert.equal(f.nets.GND, 0);
    assert.ok(typeof f.kind === 'string');
    assert.ok(f.ref === null || typeof f.ref === 'string');
    assert.ok(f.net === null || typeof f.net === 'string');
    assert.ok(Object.isFrozen(f) && Object.isFrozen(f.nets) && Object.isFrozen(f.counts));
    assert.ok(Object.isFrozen(f.pinValues) && Object.isFrozen(f.changes));
    assert.equal(Object.keys(f.pinValues).length, pinKeys.length);
    for (const value of Object.values(f.pinValues)) assert.ok(value === null || value === 0 || value === 1);
    for (const c of f.changes) {
      assert.notEqual(c.net, 'NC');
      assert.notEqual(c.from, c.to);
      assert.equal(f.nets[c.net], c.to);
      if (i && f.delta === prev + 1) assert.equal(e.frames[i - 1].nets[c.net], c.from);
      assert.ok(Object.isFrozen(c));
    }
    for (const n of analog) assert.equal(f.nets[n], null, n);
    prev = f.delta;
  }
}

const started = Date.now();

test('CSV quoting and browser/CommonJS exports', () => {
  assert.deepEqual(parseCSV('a,b\r\n"x,y","z""q\nq"\r\n'), [{a:'x,y', b:'z"q\nq'}]);
  assert.equal(F, 32768);
  assert.equal(SEG[8], 'abcdefg');
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'circuit_engine.js'), 'utf8'), context);
  assert.equal(context.CircuitEngine.F, F);
  assert.equal(context.CircuitEngine.create(COMP).display(), '00:00:00');
});

test('POR boundary and first legitimate second at 1.87 s', () => {
  const e = fresh();
  assert.equal(e.time, 0);
  assert.equal(e.nets.RST_GLOBAL, 1);
  assert.equal(e.nets.CLK1HZ, 1);
  assert.equal(e.display(), '00:00:00');
  assertFrames(e);
  e.nextEdge();
  near(e.time, 0.87);
  assert.equal(e.divider, 0);
  assert.equal(e.nets.RST_GLOBAL, 0);
  assert.equal(e.display(), '00:00:00');
  assert.ok(e.frames.some(f => f.kind === 'por'));
  for (const [t, q14, ff1] of [[1.12,1,1], [1.37,0,0], [1.62,1,0]]) {
    e.nextEdge();
    near(e.time, t);
    assert.equal(e.nets.CLK2HZ, q14);
    assert.equal(e.nets.CLK1HZ, ff1);
    assert.equal(e.display(), '00:00:00');
  }
  e.nextEdge();
  near(e.time, 1.87);
  assert.equal(e.display(), '00:00:01');
  assertFrames(e);
});

test('virtual preset seeds all clocks without a synthetic count', () => {
  const e = fresh();
  for (const [h,m,s] of [[0,0,0], [12,34,56], [23,59,59]]) {
    e.loadScenario(h,m,s);
    assert.equal(e.display(), [h,m,s].map(n => String(n).padStart(2, '0')).join(':'));
    assert.equal(e.time, 0);
    assert.equal(e.divider, 0);
    assert.equal(e.nets.POR_RST, 0);
    assert.equal(e.nets.CLK1HZ, 0);
    assert.equal(e.nets.CLK_SEC, 0);
    assert.equal(e.setMode, false);
    assert.ok(e.frames.some(f => f.kind === 'preset' && f.title.includes('مجازی')));
    const before = e.display();
    e.advance(0);
    e.nextEdge();
    assert.equal(e.display(), before);
  }
});

test('58 -> 59 -> 60 exposes the full D6_ST reset/carry pulse', () => {
  const e = fresh();
  e.loadScenario(0,0,58);
  e.advance(0.5);
  assert.equal(e.display(), '00:00:59');
  e.advance(1);
  assert.equal(e.display(), '00:01:00');
  const rise = e.frames.findIndex(f => f.nets.D6_ST === 1);
  assert.ok(rise >= 0);
  assert.equal(e.frames[rise].counts.U4, 6);
  const reset = e.frames.findIndex((f,i) => i > rise && f.nets.RST_ST === 1 && f.nets.CLK_MU === 1);
  assert.ok(reset > rise);
  const cleared = e.frames.findIndex((f,i) => i > reset && f.counts.U4 === 0 && f.counts.U5 === 1);
  assert.ok(cleared > reset);
  assert.equal(e.nets.D6_ST, 0);
  assertFrames(e);
});

test('59:59 and midnight expose D6_MT and D24 before asynchronous clears', () => {
  const e = fresh();
  for (const [hour, expected] of [[0,'01:00:00'], [23,'00:00:00']]) {
    e.loadScenario(hour,59,59);
    e.advance(0.5);
    assert.equal(e.display(), expected);
    for (const net of ['D6_ST','D6_MT', ...(hour === 23 ? ['D24'] : [])]) {
      const rise = e.frames.findIndex(f => f.nets[net] === 1);
      assert.ok(rise >= 0, net);
      assert.ok(e.frames.slice(rise + 1).some(f => f.nets[net] === 0), net + ' falls');
      assert.ok(e.frames.some(f => f.changes.some(c => c.net === net && c.from === 0 && c.to === 1)));
    }
    if (hour === 23) {
      const high = e.frames.find(f => f.nets.D24 === 1);
      assert.equal(high.counts.U8, 2);
      assert.equal(high.counts.U7, 4);
    }
    assertFrames(e);
  }
});

test('every physical pin, independent NC outputs, analog nodes unknown', () => {
  const e = fresh();
  e.loadScenario(12,34,56);
  const snap = e.snapshot();
  assert.equal(Object.keys(snap.pinValues).length, pinKeys.length);
  for (const [ref, comp] of Object.entries(COMP)) {
    for (const [pin, [,net]] of Object.entries(comp.pins)) {
      const value = e.pinValue(ref, pin);
      assert.equal(value, snap.pinValues[ref + '.' + pin]);
      if (net !== 'NC') assert.equal(value, e.nets[net]);
      else if (!/^CD/.test(comp.model)) assert.equal(value, null);
    }
  }
  assert.equal(e.pinValue('U4', 5), 0);
  assert.equal(e.pinValue('U6', 5), 1);
  assert.equal(e.pinValue('U4', 4), 1);
  assert.equal(e.pinValue('U8', 14), 1);
  assert.equal(e.pinValue('U13', 11), 0);
  assert.equal(e.pinValue('U1', 9), null);
  assert.equal(e.pinValue('U1', 10), null);
  assert.equal(e.pinValue('U1', 11), null);
  assert.equal(e.nets.NC, null);
  assert.equal(e.pinValue('missing', 1), null);
  assert.equal(e.pinValue('U1', 99), null);
  for (const n of analog) assert.equal(e.nets[n], null, n);
  e.loadScenario(20,0,0);
  assert.equal(e.pinValue('U8', 14), 0);
  assertFrames(e);
});

test('CD4026 truth table, carry, ungated C and real segment pin numbers', () => {
  const e = fresh();
  const segments = [[10,'a'],[12,'b'],[13,'c'],[9,'d'],[11,'e'],[6,'f'],[7,'g']];
  for (let n = 0; n < 10; n++) {
    e.loadScenario(0,0,n);
    assert.equal(e.pinValue('U3',4), 1);
    assert.equal(e.pinValue('U3',5), Number(n < 5));
    assert.equal(e.pinValue('U3',14), Number(n !== 2));
    for (const [pin,segment] of segments) assert.equal(e.pinValue('U3',pin), Number(SEG[n].includes(segment)));
  }
});

test('all CD4060 taps track fractional and intermediate crystal counts', () => {
  const e = fresh();
  e.loadScenario(0,0,0);
  e.advance(0.4 / F);
  e.advance(0.4 / F);
  assert.equal(e.divider, 0);
  e.advance(0.2 / F);
  assert.equal(e.divider, 1);
  const taps = [[7,4], [5,5], [4,6], [6,7], [14,8], [13,9], [15,10], [1,12], [2,13], [3,14]];
  let old = 1;
  for (const cycles of [7,8,16,32,64,128,256,512,2048,4096,8192,16383,16384]) {
    e.advance((cycles - old) / F);
    assert.equal(e.divider, cycles % 16384);
    for (const [pin, bit] of taps) assert.equal(e.pinValue('U1', pin), (cycles >> (bit - 1)) & 1);
    old = cycles;
  }
  e.crystalStep();
  assert.equal(e.divider, 1);
  assert.equal(e.nets.NC, null);
});

test('button edges, SET gating, hold once, seconds versus global reset', () => {
  const e = fresh();
  e.loadScenario(12,34,56);
  tap(e, 'HOUR'); tap(e, 'MIN');
  assert.equal(e.display(), '12:34:56');
  e.press('SET');
  assert.equal(e.setMode, true);
  e.press('SET');
  assert.equal(e.setMode, true);
  e.release('SET');
  e.press('HOUR'); e.press('HOUR');
  assert.equal(e.display(), '13:34:56');
  e.advance(2);
  assert.equal(e.display(), '13:34:56');
  e.release('HOUR'); tap(e, 'MIN');
  assert.equal(e.display(), '13:35:56');
  tap(e, 'SET');
  assert.equal(e.setMode, false);
  e.press('SECRST');
  assert.equal(e.display(), '13:35:00');
  e.advance(2);
  assert.equal(e.display(), '13:35:00');
  e.release('SECRST');
  e.advance(0.5);
  assert.equal(e.display(), '13:35:01');
  e.press('MSTRST');
  assert.equal(e.display(), '00:00:00');
  assert.equal(e.divider, 0);
  assert.equal(e.setMode, false);
  e.advance(3.25);
  assert.equal(e.divider, 0);
  assert.equal(e.display(), '00:00:00');
  const heldTime = e.time;
  e.nextEdge();
  assert.equal(e.time, heldTime);
  e.release('MSTRST');
  assert.equal(e.display(), '00:00:00');
  e.advance(0.999);
  assert.equal(e.display(), '00:00:00');
  e.advance(0.001);
  assert.equal(e.display(), '00:00:01');
  assertFrames(e);
});

test('SET exit while CLK1HZ high produces the real extra gated rising edge', () => {
  const e = fresh();
  e.loadScenario(0,0,10);
  e.advance(0.5);
  assert.equal(e.display(), '00:00:11');
  assert.equal(e.nets.CLK1HZ, 1);
  tap(e, 'SET');
  assert.equal(e.nets.CLK_SEC, 0);
  assert.equal(e.setMode, true);
  // This netlist gates a level, not a glitch-free clock: exiting SET adds an edge.
  e.press('SET');
  assert.equal(e.setMode, false);
  assert.equal(e.display(), '00:00:12');
  assert.ok(e.frames.some(f => f.changes.some(c => c.net === 'CLK_SEC' && c.from === 0 && c.to === 1)));
  assertFrames(e);
  e.release('SET');
  assert.equal(e.display(), '00:00:12');
});

test('power off halts time and makes every non-ground pin unknown; power on restarts POR', () => {
  const e = fresh();
  e.loadScenario(12,34,56);
  e.advance(0.12345);
  e.powerOff();
  const before = e.snapshot();
  assert.equal(e.powered, false);
  for (const [net, value] of Object.entries(e.nets)) assert.equal(value, net === 'GND' ? 0 : null, net);
  for (const [ref,c] of Object.entries(COMP)) for (const [pin,p] of Object.entries(c.pins)) {
    assert.equal(e.pinValue(ref,pin), p[1] === 'GND' ? 0 : null, ref + '.' + pin);
  }
  e.advance(10); e.nextEdge(); e.crystalStep();
  assert.deepEqual(e.snapshot(), before);
  e.powerOn();
  assert.equal(e.time, 0);
  assert.equal(e.divider, 0);
  assert.equal(e.display(), '00:00:00');
  assert.equal(e.nets.POR_RST, 1);
  e.advance(1.87);
  assert.equal(e.display(), '00:00:01');
  assertFrames(e);
});

test('fractional chunks equal a single advance across POR and later boundaries', () => {
  const chunks = [0.000001, 0.1234567, 0.25, 0.4965, 0.00006, 0.25, 0.25, 0.49999, 2.3456789];
  const a = fresh(), b = fresh();
  a.advance(chunks.reduce((x,y) => x + y, 0));
  for (const dt of chunks) b.advance(dt);
  sameState(a,b);
  a.advance(0.000071); b.advance(0.000071);
  sameState(a,b);
  const c = fresh(), d = fresh();
  c.advance(1.9);
  for (let i = 0; i < 1900; i++) d.advance(0.001);
  sameState(c,d);
  const x = fresh(), y = fresh();
  x.loadScenario(0,0,0); y.loadScenario(0,0,0);
  x.advance(81.3 / F);
  for (let i = 0; i < 271; i++) y.advance(0.3 / F);
  sameState(x,y);
  x.advance(0.7 / F); y.advance(0.7 / F);
  sameState(x,y);
  assert.equal(x.divider, 82);
});

test('actual gate inputs, inhibit and display enable drive the model', () => {
  const modified = clone();
  modified.U11.pins['6'][1] = 'GND';
  const blocked = create(modified), normal = fresh();
  blocked.advance(2.87); normal.advance(2.87);
  assert.equal(normal.display(), '00:00:02');
  assert.equal(blocked.display(), '00:00:00');
  assert.equal(blocked.nets.CLK_SEC, 0);
  const inhibited = clone();
  inhibited.U3.pins['2'][1] = 'VCC';
  const stop = create(inhibited);
  stop.advance(2.87);
  assert.equal(stop.display(), '00:00:00');
  const blanked = clone();
  blanked.U3.pins['3'][1] = 'GND';
  const off = create(blanked);
  off.loadScenario(0,0,2);
  for (const pin of [4,10,12,13,9,11,6,7]) assert.equal(off.pinValue('U3',pin), 0);
  assert.equal(off.pinValue('U3',14), 0);
  assert.equal(off.pinValue('U3',5), 1);
  off.advance(0.5);
  assert.equal(off.counts.U3, 3);
  assert.equal(off.pinValue('U3',14), 1);
});

test('disabled decoders remove modulo-6/modulo-24 behavior instead of forcing rollover', () => {
  const noSix = clone();
  noSix.U9.pins['6'][1] = 'GND';
  const e = create(noSix);
  e.loadScenario(0,0,59);
  e.advance(0.5);
  assert.equal(e.display(), '00:00:60');
  assert.equal(e.nets.D6_ST, 0);
  const noTwentyFour = clone();
  noTwentyFour.U11.pins['1'][1] = 'GND';
  const f = create(noTwentyFour);
  f.loadScenario(23,59,59);
  f.advance(0.5);
  assert.equal(f.display(), '24:00:00');
  assert.equal(f.nets.D24, 0);
});

test('manual rollovers and master reset held across POR obey the same gates', () => {
  const e = fresh();
  e.loadScenario(23,59,56);
  tap(e, 'SET'); tap(e, 'HOUR');
  assert.equal(e.display(), '00:59:56');
  tap(e, 'MIN');
  assert.equal(e.display(), '01:00:56');
  e.powerOn();
  e.press('MSTRST');
  e.advance(2.1);
  assert.equal(e.nets.POR_RST, 0);
  assert.equal(e.nets.RST_GLOBAL, 1);
  assert.equal(e.divider, 0);
  assert.equal(e.display(), '00:00:00');
  e.release('MSTRST');
  e.advance(1);
  assert.equal(e.display(), '00:00:01');
  const resetWiredHigh = clone();
  resetWiredHigh.U3.pins['15'][1] = 'VCC';
  const f = create(resetWiredHigh);
  f.loadScenario(0,0,3);
  assert.equal(f.counts.U3, 0);
  f.advance(0.5);
  assert.equal(f.nets.CLK_SEC, 1);
  assert.equal(f.counts.U3, 0);
});

test('internal net renaming and a connected low divider tap need no hardcoded wiring', () => {
  const renamed = clone();
  for (const c of Object.values(renamed)) for (const p of Object.values(c.pins)) {
    if (!['NC','VCC','GND','POR_N'].includes(p[1])) p[1] = 'RENAMED_' + p[1];
  }
  const e = create(renamed);
  e.advance(1.87);
  assert.equal(e.display(), '00:00:01');
  tap(e, 'SET'); tap(e, 'MIN');
  assert.equal(e.setMode, true);
  assert.equal(e.display(), '00:01:01');
  e.loadScenario(23,59,59); e.advance(0.5);
  assert.equal(e.display(), '00:00:00');
  assert.equal(e.nets.CLK1HZ, undefined);
  const fast = clone();
  fast.U1.pins['7'][1] = 'FAST_TAP';
  fast.U3.pins['1'][1] = 'FAST_TAP';
  const f = create(fast);
  f.loadScenario(0,0,0);
  f.advance(40 / F);
  assert.equal(f.counts.U3, 3); // Q4 rises at cycles 8, 24, 40, even in one call.
  assert.equal(f.pinValue('U1',7), 1);
});

test('immutable complete snapshots, bounded history, final frame retained', () => {
  const e = fresh();
  e.loadScenario(23,59,59);
  e.advance(0.5);
  const saved = e.snapshot(), priorFrames = e.frames;
  const serialized = JSON.stringify({saved, priorFrames});
  assert.throws(() => { saved.nets.VCC = 9; }, TypeError);
  assert.throws(() => { saved.counts.U3 = 9; }, TypeError);
  assert.throws(() => { saved.pinValues['U1.1'] = 9; }, TypeError);
  assert.throws(() => { priorFrames[0].title = 'changed'; }, TypeError);
  e.advance(3600);
  assert.equal(e.frames.length, 512);
  assertFrames(e);
  assert.equal(JSON.stringify({saved, priorFrames}), serialized);
  e.press('SECRST');
  assert.ok(e.frames.length < 512);
  assertFrames(e);
});

test('25-hour run: 90061 seconds after POR, including midnight', () => {
  const e = fresh();
  e.advance(0.87 + 90061);
  near(e.time, 90061.87);
  assert.equal(e.display(), '01:01:01');
  assert.equal(e.divider, 0);
  assert.equal(e.nets.D6_ST, 0);
  assert.equal(e.nets.D6_MT, 0);
  assert.equal(e.nets.D24, 0);
  assert.equal(e.frames.length, 512);
  assertFrames(e);
});

test('input validation is non-mutating', () => {
  const e = fresh(), before = e.snapshot();
  for (const dt of [-1,NaN,Infinity,'1',null]) assert.throws(() => e.advance(dt), RangeError);
  for (const args of [[24,0,0],[-1,0,0],[0,60,0],[0,0,60],[1.5,0,0],[0,0,-1],[0,NaN,0]]) {
    assert.throws(() => e.loadScenario(...args), RangeError);
  }
  assert.throws(() => e.press('OTHER'), RangeError);
  assert.throws(() => e.release('OTHER'), RangeError);
  assert.deepEqual(e.snapshot(), before);
  assert.throws(() => create(), TypeError);
});

console.log(`${passed} tests passed in ${((Date.now() - started) / 1000).toFixed(2)} s; ${pinKeys.length} physical pins checked.`);
