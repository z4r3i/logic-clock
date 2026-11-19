'use strict';
const {create,SEG}=require('./clock_engine.js');
function ref(s){const h=Math.floor(s/3600)%24,m=Math.floor(s/60)%60,x=s%60;
  const p=n=>String(n).padStart(2,'0');return p(h)+':'+p(m)+':'+p(x);}
function near(a,b,eps=1e-9){if(Math.abs(a-b)>eps)throw new Error('time expected '+b+', got '+a);}
function boot(){const e=create();e.powerOn();e.step(0.87);return e;}

// POR must hold the timebase: first CLK1HZ rising edge is 1.000 s after
// release, i.e. at 1.87 s after power-on.
let e=create();e.powerOn();
e.step(0.86);if(e.display()!=='00:00:00')throw new Error('tick during POR');
e.step(0.01);near(e.simTime,0.87);if(e.display()!=='00:00:00')throw new Error('tick at POR release');
e.step(0.99);near(e.simTime,1.86);if(e.display()!=='00:00:00')throw new Error('early first tick');
e.step(0.01);near(e.simTime,1.87);if(e.display()!=='00:00:01')throw new Error('first tick not at 1.87 s');
e=create();e.powerOn();e.step(1.86);
if(e.display()!=='00:00:00')throw new Error('split POR step leaked cycles');
e.step(0.01);if(e.display()!=='00:00:01')throw new Error('split POR first tick');
console.log('POR/first-tick OK (1.87 s)');

// Invalid steps must throw even while powered off (state must not change).
e.powerCycle();
for(const bad of [-1,NaN,Infinity,'1']){
  let threw=false;try{e.step(bad);}catch(err){threw=err instanceof RangeError;}
  if(!threw) throw new Error('invalid step accepted: '+bad);
}
if(e.simTime!==1.87) throw new Error('invalid step mutated time');
e.powerOn();
console.log('input validation OK');

// 25h+ sequence: one step(1s) after POR == one CLK1HZ rising edge == one second
e=boot();
let bad=0;
for(let s=1;s<=90061;s++){ e.step(1); if(e.display()!==ref(s)){ if(bad<5)console.log('MISMATCH',s,e.display(),ref(s)); bad++; } }
console.log('sequence 90061s mismatches='+bad+' carrySecMin='+e.carryCount.secMin+' carryMinHour='+e.carryCount.minHour);
if(bad) throw new Error('sequence fail');
if(e.carryCount.secMin!==Math.floor(90061/60)) throw new Error('secMin carry count');
if(e.carryCount.minHour!==Math.floor(90061/3600)) throw new Error('minHour carry count');

// boundaries
e=boot(); let s=0;
for(const [t,exp] of [[58,'00:00:58'],[60,'00:01:00'],[3599,'00:59:59'],[3600,'01:00:00'],[86399,'23:59:59'],[86400,'00:00:00'],[86401,'00:00:01']]){
  while(s<t){e.step(1);s++;}
  console.log('t='+t+' '+e.display()+' expect '+exp+(e.display()===exp?' OK':' FAIL'));
  if(e.display()!==exp) throw new Error('boundary fail');
}

// 60 fps must not drift: 3600 one-second steps at dt=1/60
e=boot();
for(let i=0;i<3600*60;i++) e.step(1/60);
if(e.display()!=='01:00:00'){
  throw new Error('60fps drift: '+e.display()+' at '+e.simTime.toFixed(3)+' s');
}
console.log('60fps drift OK: 01:00:00 after 3600 s');

// set/reset
e=boot(); for(let i=0;i<5;i++)e.step(1);   // 00:00:05
e.press('SET'); e.release('SET');           // enter set mode
if(!e.setMode) throw new Error('set mode not entered');
const frozen=e.display(); for(let i=0;i<10;i++)e.step(1);
if(e.display()!==frozen) throw new Error('seconds not frozen in set');
for(let i=0;i<3;i++){e.press('MIN');e.release('MIN');}
for(let i=0;i<2;i++){e.press('HOUR');e.release('HOUR');}
console.log('after +3min +2hour: '+e.display());
if(e.display()!=='02:03:05') throw new Error('manual set wrong');
e.press('SECRST'); e.release('SECRST');
if(e.display()!=='02:03:00') throw new Error('sec reset wrong');
e.press('SET'); e.release('SET'); e.step(1);
if(e.display()!=='02:03:01') throw new Error('resume wrong');
e.press('MSTRST'); e.release('MSTRST');
if(e.display()!=='00:00:00') throw new Error('master reset wrong');
console.log('set/reset OK');

// decode uniqueness on reachable states
const d6=n=>SEG[n].includes('e')&&SEG[n].includes('f')&&SEG[n].includes('g');
for(let n=0;n<=5;n++) if(d6(n)) throw new Error('d6 false positive '+n);
if(!d6(6)) throw new Error('d6 misses 6');
console.log('decode uniqueness OK');
console.log('ALL ENGINE TESTS PASSED');
