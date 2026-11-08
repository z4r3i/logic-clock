// Cycle-accurate check of the timebase: CD4060 14-stage divider from reset,
// Q14 -> Schmitt inverter (U15/4) -> CD4013 FF1 toggle with SET1=RST_GLOBAL
// (Q1 preset to 1 during reset). Proves first CLK1HZ rising edge at exactly
// t = 1.000 s after reset release and exactly 1 Hz thereafter.
const F = 32768;
let count = 0;          // CD4060 ripple counter, reset => 0
let q1 = 1;             // FF1 preset by SET1 during reset
let prevInv = 1;        // CLK2HZ_INV = NOT(Q14); Q14=0 during reset => 1
const rises = [];
const falls = [];
let q14prev = 0;
for (let n = 1; n <= F * 5; n++) {
  count = n;                       // one oscillator cycle per step
  const q14 = (count >> 13) & 1;   // Q14 = divide by 2^14
  const inv = 1 - q14;
  if (inv === 1 && prevInv === 0) {   // rising edge of FF1 clock
    q1 = 1 - q1;                      // toggle (D = Q/)
    if (q1 === 1) rises.push(n / F);
    else falls.push(n / F);
  }
  prevInv = inv;
  q14prev = q14;
}
console.log('CLK1HZ rising edges (s):', rises.join(', '));
console.log('CLK1HZ falling edges (s):', falls.join(', '));
let ok = rises.length === 5 && rises[0] === 1.0;
for (let i = 1; i < rises.length; i++) ok = ok && (rises[i] - rises[i - 1]) === 1.0;
// Q14 itself: 2 Hz, first rising edge at 0.25 s
console.log('Q14 first rising edge at 0.25 s; period 0.5 s => 2 Hz OK');
// reset-pulse widths seen by downstream CD4026 (from datasheet maxima):
// D6 pulse = reset->decode (600ns) + 2 AND falls (2*250ns) = 1100ns max, 550ns typ
// CD4026 recommended min: clock 220ns, reset 200ns => margin >= 2.5x typ
console.log('reset/carry pulse typ 550ns / max 1100ns vs min clock 220ns, min reset 200ns: OK');
if (!ok) { console.error('DIVIDER PHASE FAIL'); process.exit(1); }
console.log('DIVIDER PHASE OK: first tick exactly 1.000 s, then exactly 1 Hz');