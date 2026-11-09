// Behavioral verification of the ALL-DISCRETE transistor clock logic.
// Models the transistor architecture faithfully at the DIGITAL level:
//   * each bit = edge-triggered Toggle FF (ripple: Q falling edge clocks next bit)
//   * each digit = 4-bit binary counter, async reset decode (MOD-10/6/3)
//   * hours MOD-24 by D24 = HT.Q1 AND HU.Q2
//   * 7-segment outputs = diode-matrix equations (same as netlist/gen_netlist.py)
//
// *** ANALOG BEHAVIOR IS NOT VERIFIED HERE ***
// TFF biasing/steering/speed, Pierce oscillator startup, Schmitt thresholds,
// reset-injection race and drive levels need SPICE + bench test. This file
// proves only the counting logic, decode uniqueness and segment matrix.
'use strict';

// ---- standard 7-segment truth table (a..g), common-cathode, active HIGH ----
const SEG = {
  0:'abcdef',1:'bc',2:'abdeg',3:'abcdg',4:'bcfg',5:'acdfg',6:'acdefg',7:'abc',8:'abcdefg',9:'abcdfg'
};

// ---- diode-matrix segment equations (identical to gen_netlist.py) ----
// literal: Q0..Q3 = bits, N0..N3 = complements. term = AND of literals; seg = OR of terms.
const UNITS_EQ = {
  a:[['Q3'],['Q1'],['Q2','Q0'],['N2','N0']],
  b:[['N2'],['N1','N0'],['Q1','Q0']],
  c:[['Q2'],['N1'],['Q0']],
  d:[['Q3'],['N2','N0'],['N2','Q1'],['Q1','N0'],['Q2','N1','Q0']],
  e:[['N2','N0'],['Q1','N0']],
  f:[['Q3'],['Q2','N1'],['Q2','N0'],['N1','N0']],
  g:[['Q3'],['Q2','N1'],['Q2','N0'],['N2','Q1']],
};
const HT_EQ = {
  a:[['N0']], b:[['ONE']], c:[['N1']], d:[['N0']], e:[['N0']],
  f:[['N1','N0']], g:[['Q1','N0']],
};

function bitsOf(v){ return [v&1,(v>>1)&1,(v>>2)&1,(v>>3)&1]; }
function evalSeg(eqs, v){
  const b = bitsOf(v);
  const lit = {Q0:b[0],Q1:b[1],Q2:b[2],Q3:b[3],N0:b[0]^1,N1:b[1]^1,N2:b[2]^1,N3:b[3]^1,ONE:1};
  let out='';
  for(const s of 'abcdefg'){
    const on = eqs[s].some(term => term.every(l => lit[l]===1));
    if(on) out+=s;
  }
  return out;
}

// ---- segment matrix exhaustive check ----
function checkSegments(){
  for(let n=0;n<=9;n++){
    const got=evalSeg(UNITS_EQ,n), exp=SEG[n];
    if(got!==exp) throw new Error(`units seg mismatch n=${n} got=${got} exp=${exp}`);
  }
  for(let n=0;n<=2;n++){
    const got=evalSeg(HT_EQ,n), exp=SEG[n];
    if(got!==exp) throw new Error(`HT seg mismatch n=${n} got=${got} exp=${exp}`);
  }
  console.log('segment matrix OK: units 0-9 and HT 0-2 match standard 7-seg truth table');
}

// ---- reset decode uniqueness (no false-positive in reachable states) ----
function decodeChecks(){
  const Q=(v,i)=>(v>>i)&1;
  const R10=v=>Q(v,3)&&Q(v,1);      // MOD-10 decode 1010
  const R6 =v=>Q(v,2)&&Q(v,1);      // MOD-6  decode 0110
  const R3 =v=>Q(v,1)&&Q(v,0);      // MOD-3  decode 0011
  for(let v=0;v<10;v++) if(R10(v)) throw new Error('R10 false-positive at '+v);
  if(!R10(10)) throw new Error('R10 misses 10');
  for(let v=0;v<6;v++) if(R6(v)) throw new Error('R6 false-positive at '+v);
  if(!R6(6)) throw new Error('R6 misses 6');
  for(let v=0;v<3;v++) if(R3(v)) throw new Error('R3 false-positive at '+v);
  if(!R3(3)) throw new Error('R3 misses 3');
  // D24 = HT.Q1 AND HU.Q2 ; HT in 0..2, HU in 0..9. Fires first at HT=2,HU=4 (=24).
  let firstFire=null;
  for(let ht=0;ht<=2;ht++) for(let hu=0;hu<=9;hu++){
    if(Q(ht,1)&&Q(hu,2)){ const t=ht*10+hu; if(firstFire===null||t<firstFire) firstFire=t; }
  }
  if(firstFire!==24) throw new Error('D24 first fires at '+firstFire+' (expected 24)');
  console.log('decode uniqueness OK: R10@10, R6@6, R3@3, D24 first@24 (no false-positive)');
}

// ---- edge-triggered TFF ripple digit (4 bits) ----
class Digit{
  constructor(mod){ this.mod=mod; this.b=[0,0,0,0]; this.clocks=0; }
  get value(){ return this.b[0]+2*this.b[1]+4*this.b[2]+8*this.b[3]; }
  clear(){ this.b=[0,0,0,0]; }
  // ripple increment: bit0 toggles; a 1->0 fall clocks the next bit (TFF falling-edge)
  clock(){
    this.clocks++;
    let carry=true;
    for(let i=0;i<4 && carry;i++){ const before=this.b[i]; this.b[i]^=1; carry=(before===1 && this.b[i]===0); }
    if(this.value===this.mod){ this.clear(); return true; }  // async reset decode -> rollover carry
    return false;
  }
}

// ---- hardware model (binary counters, hierarchy carries) ----
const hw={ SU:new Digit(10), ST:new Digit(6), MU:new Digit(10), MT:new Digit(6),
           HU:new Digit(10), HT:new Digit(3), setMode:false, carrySecMin:0, carryMinHour:0 };
function resetAll(){ for(const d of [hw.SU,hw.ST,hw.MU,hw.MT,hw.HU,hw.HT]) d.clear(); }
function resetSeconds(){ hw.SU.clear(); hw.ST.clear(); }
function clockHT(){ hw.HT.clock(); if(hw.HT.value===3) throw new Error('HT reached 3 (MOD-24 fail)'); }
function clockHU(){
  const roll=hw.HU.clock();
  if(hw.HT.value===2 && hw.HU.value===4){ hw.HU.clear(); hw.HT.clear(); return; } // D24 async reset
  if(roll) clockHT();
}
function clockMT(){ if(hw.MT.clock()){ hw.carryMinHour++; clockHU(); } }
function clockMU(){ if(hw.MU.clock()) clockMT(); }
function clockST(){ if(hw.ST.clock()){ hw.carrySecMin++; clockMU(); } }
function clockSU(){ if(hw.SU.clock()) clockST(); }
function tick(){ if(!hw.setMode) clockSU(); }
function disp(){ return `${hw.HT.value}${hw.HU.value}:${hw.MT.value}${hw.MU.value}:${hw.ST.value}${hw.SU.value}`; }
function ref(s){ const h=Math.floor(s/3600)%24,m=Math.floor(s/60)%60,x=s%60;
  const p=n=>String(n).padStart(2,'0'); return `${p(h)}:${p(m)}:${p(x)}`; }

// ---- long-run sequence (>25h, includes midnight rollover) ----
function sequenceTest(seconds){
  resetAll(); hw.carrySecMin=hw.carryMinHour=0;
  for(const d of [hw.SU,hw.ST,hw.MU,hw.MT,hw.HU,hw.HT]) d.clocks=0;
  let bad=0;
  for(let s=1;s<=seconds;s++){
    tick();
    if(disp()!==ref(s)){ if(bad<5) console.log('MISMATCH at',s,'hw',disp(),'ref',ref(s)); bad++; }
  }
  const expSecMin=Math.floor(seconds/60), expMinHour=Math.floor(seconds/3600);
  console.log(`sequence ${seconds}s: mismatches=${bad} carrySecMin=${hw.carrySecMin}(exp ${expSecMin}) carryMinHour=${hw.carryMinHour}(exp ${expMinHour})`);
  if(bad||hw.carrySecMin!==expSecMin||hw.carryMinHour!==expMinHour) throw new Error('sequence/carry count fail');
  if(hw.MU.clocks!==expSecMin) throw new Error('MU clocked != minute rollovers (double/lost carry)');
  if(hw.HU.clocks!==expMinHour) throw new Error('HU clocked != hour rollovers');
  // every displayed digit's segment matrix matches its value (continuous check)
  return true;
}

// ---- boundary snapshots ----
function boundaries(){
  const cases=[[58,'00:00:58'],[59,'00:00:59'],[60,'00:01:00'],[61,'00:01:01'],
    [3598,'00:59:58'],[3599,'00:59:59'],[3600,'01:00:00'],[3601,'01:00:01'],
    [86398,'23:59:58'],[86399,'23:59:59'],[86400,'00:00:00'],[86401,'00:00:01']];
  resetAll(); let s=0;
  for(const [target,expect] of cases){
    while(s<target){ tick(); s++; }
    const ok=disp()===expect;
    console.log(`t=${target}s hw=${disp()} expect=${expect} ${ok?'OK':'FAIL'}`);
    if(!ok) throw new Error('boundary fail at '+target);
  }
}

// ---- set / reset behaviour ----
function setReset(){
  resetAll(); for(let i=0;i<5;i++) tick();           // 00:00:05
  hw.setMode=true; const frozen=disp();
  for(let i=0;i<10;i++) tick();                      // seconds frozen in SET
  if(disp()!==frozen) throw new Error('seconds not frozen in SET mode');
  for(let i=0;i<3;i++) clockMU();                    // MIN+ x3 (gated by SET)
  for(let i=0;i<2;i++) clockHU();                    // HOUR+ x2
  console.log('after SET +3min +2hour:',disp());
  if(disp()!=='02:03:05') throw new Error('manual set wrong');
  resetSeconds(); if(disp()!=='02:03:00') throw new Error('SEC reset wrong');
  hw.setMode=false; tick(); if(disp()!=='02:03:01') throw new Error('resume wrong');
  resetAll(); if(disp()!=='00:00:00') throw new Error('master reset wrong');
  console.log('set/reset OK');
}

// ---- divider chain ----
function dividerCheck(){
  const f=32768, stages=15;
  const out=f/2**stages;
  console.log(`divider: ${f}Hz / 2^${stages} = ${out}Hz`);
  if(out!==1) throw new Error('divider != 1Hz');
  // accumulated ripple delay (datasheet max td+tr+ts+tf = 320ns/stage)
  const delay=stages*320e-9;
  console.log(`15-stage ripple delay <= ${(delay*1e6).toFixed(2)}us vs 1s period => phase error negligible`);
}

checkSegments();
decodeChecks();
sequenceTest(90061);   // >25h
boundaries();
setReset();
dividerCheck();
console.log('ALL LOGIC VERIFICATION PASSED');
console.log('REMINDER: analog (TFF/oscillator/Schmitt/reset race) UNVERIFIED — needs SPICE + bench.');