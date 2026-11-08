// Functional + timing verification of the CD4026-based 24h logic clock.
// Mirrors netlist semantics: CD4026 Johnson decade (natural MOD-10, CARRY OUT
// rising edge at 9->0), tens digits forced MOD-6 by segment decode e.f.g feeding
// async RESET (same pulse = carry to next group), hours MOD-24 by decode24.
'use strict';

const SEG = { // CD4026 decoded segments a..g per count
  0:'abcdef',1:'bc',2:'abdeg',3:'abcdg',4:'bcfg',5:'acdfg',6:'acdefg',7:'abc',8:'abcdefg',9:'abcdfg'
};
const has = (n,s)=>SEG[n].includes(s);

// ---- hardware model ----
const hw = {
  SU:0, ST:0, MU:0, MT:0, HU:0, HT:0,
  carrySecMin:0, carryMinHour:0, clkMU:0, clkHU:0, clkST:0, clkMT:0, clkHT:0,
  setMode:false,
};
function resetAll(){ hw.SU=hw.ST=hw.MU=hw.MT=hw.HU=hw.HT=0; }
function resetSeconds(){ hw.SU=0; hw.ST=0; }

function clockHU(){ // hours units clock edge
  hw.clkHU++;
  hw.HU++;
  if (hw.HT===2 && hw.HU===4){ hw.HU=0; hw.HT=0; return; } // decode24 async reset both
  if (hw.HU===10){ hw.HU=0; clockHT(); }                   // CARRY OUT -> tens
}
function clockHT(){ hw.clkHT++; hw.HT++; if (hw.HT===3) throw new Error('hours tens reached 3 (MOD-24 fail)'); }
function clockMT(){ hw.clkMT++; hw.MT++; if (hw.MT===6){ hw.MT=0; hw.carryMinHour++; clockHU(); } } // decode6 reset+carry
function clockMU(){ hw.clkMU++; hw.MU++; if (hw.MU===10){ hw.MU=0; clockMT(); } }
function clockST(){ hw.clkST++; hw.ST++; if (hw.ST===6){ hw.ST=0; hw.carrySecMin++; clockMU(); } } // decode6 reset+carry
function clockSU(){ hw.SU++; if (hw.SU===10){ hw.SU=0; clockST(); } }

function tick(){ if(!hw.setMode) clockSU(); }
function disp(){ return `${hw.HT}${hw.HU}:${hw.MT}${hw.MU}:${hw.ST}${hw.SU}`; }
function ref(s){ const h=Math.floor(s/3600)%24,m=Math.floor(s/60)%60,x=s%60;
  const p=n=>String(n).padStart(2,'0'); return `${p(h)}:${p(m)}:${p(x)}`; }

// ---- decode uniqueness checks (Johnson reachable states) ----
function decodeChecks(){
  const d6=n=>has(n,'e')&&has(n,'f')&&has(n,'g');
  for(let n=0;n<=5;n++) if(d6(n)) throw new Error('decode6 false-positive at '+n);
  if(!d6(6)) throw new Error('decode6 misses 6');
  const t2=n=>has(n,'a')&&has(n,'d')&&has(n,'g');
  for(let n=0;n<=2;n++) if(t2(n)!==(n===2)) throw new Error('tens-is-2 wrong at '+n);
  const u4=n=>has(n,'c')&&has(n,'f')&&has(n,'g');
  for(let n=0;n<=4;n++) if(u4(n)!==(n===4)) throw new Error('units-is-4 wrong at '+n);
  return true;
}

// ---- long-run sequence test ----
function sequenceTest(seconds){
  resetAll(); hw.carrySecMin=hw.carryMinHour=hw.clkMU=hw.clkHU=0;
  let bad=0;
  for(let s=1;s<=seconds;s++){
    tick();
    if(disp()!==ref(s)){ if(bad<5) console.log('MISMATCH at',s,'hw',disp(),'ref',ref(s)); bad++; }
  }
  const expSecMin=Math.floor(seconds/60), expMinHour=Math.floor(seconds/3600);
  console.log(`sequence ${seconds}s: mismatches=${bad} carrySecMin=${hw.carrySecMin}(exp ${expSecMin}) carryMinHour=${hw.carryMinHour}(exp ${expMinHour})`);
  if(bad||hw.carrySecMin!==expSecMin||hw.carryMinHour!==expMinHour) throw new Error('sequence/carry count fail');
  // one clock edge per carry into MU/HU (no double count)
  if(hw.clkMU!==expSecMin) throw new Error('MU clocked != minute rollovers (double/lost carry)');
  if(hw.clkHU!==expMinHour) throw new Error('HU clocked != hour rollovers');
  return true;
}

// ---- boundary snapshots ----
function boundaries(){
  const cases=[[58,'00:00:58'],[59,'00:00:59'],[60,'00:01:00'],[61,'00:01:01'],
    [3598,'00:59:58'],[3599,'00:59:59'],[3600,'01:00:00'],[3601,'01:00:01'],
    [86398,'23:59:58'],[86399,'23:59:59'],[86400,'00:00:00'],[86401,'00:00:01']];
  resetAll();
  let s=0;
  for(const [target,expect] of cases){
    while(s<target){ tick(); s++; }
    const ok=disp()===expect;
    console.log(`t=${target}s hw=${disp()} expect=${expect} ${ok?'OK':'FAIL'}`);
    if(!ok) throw new Error('boundary fail');
  }
}

// ---- set / reset behaviour ----
function setReset(){
  resetAll(); for(let i=0;i<5;i++) tick();           // 00:00:05
  hw.setMode=true; const frozen=disp();
  for(let i=0;i<10;i++) tick();                      // seconds must stay frozen
  if(disp()!==frozen) throw new Error('seconds not frozen in SET mode');
  // manual MIN+ x3 and HOUR+ x2 (gated by setMode)
  for(let i=0;i<3;i++) clockMU();
  for(let i=0;i<2;i++) clockHU();
  console.log('after SET +3min +2hour:',disp());
  if(disp()!=='02:03:05') throw new Error('manual set wrong');
  resetSeconds(); if(disp()!=='02:03:00') throw new Error('SEC reset wrong');
  hw.setMode=false; tick(); if(disp()!=='02:03:01') throw new Error('resume wrong');
  resetAll(); if(disp()!=='00:00:00') throw new Error('master reset wrong');
  console.log('set/reset OK');
}

// ---- pulse-width / timing margins (datasheet typ & max, 5V) ----
function timing(){
  const gAND=125, gANDmax=250;             // CD4081 tP @5V typ/max
  const rst2dec=300, rst2decMax=600;       // CD4026 reset->decode typ/max
  const clk2dec=350;                       // CD4026 clock->decode typ
  // MOD-6 self-reset pulse = reset->decode + 2 AND fall delays
  const resetPulseTyp=rst2dec+2*gAND, resetPulseMax=rst2decMax+2*gANDmax;
  // same pulse is the carry clocking next CD4026
  const needReset=200, needClk=220;        // recommended min widths @5V
  console.log(`MOD-6 reset/carry pulse: typ=${resetPulseTyp}ns max=${resetPulseMax}ns; required reset>=${needReset}ns clock>=${needClk}ns`);
  if(resetPulseTyp<needClk) throw new Error('carry pulse too short');
  // guaranteed-min corner: reset->decode has no min spec; use min reset pulse the
  // device accepts (120ns max) as lower bound sanity: our pulse >> that.
  console.log('device min reset pulse accepted (max limit)=120ns; min clock pulse accepted (max limit)=220ns; generated pulse typ 550ns => margin OK');
  // 1Hz chain: 32768 / 2^14 = 2Hz (Q14); /2 by CD4013 = 1Hz
  console.log('Q14 =',32768/2**14,'Hz; after CD4013 /2 =',32768/2**14/2,'Hz');
}

decodeChecks(); console.log('decode uniqueness OK');
sequenceTest(90061);   // >25h includes midnight rollover
boundaries();
setReset();
timing();
console.log('ALL VERIFICATION PASSED');