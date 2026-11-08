// Net-driven functional simulator of the CD4026 hardware clock.
// Mirrors netlist/gen_netlist.py: real nets, real gates, real IC behaviour.
// Timebase is cycle-accurate: CD4060 counts 32768 Hz crystal edges; Q14 -> Schmitt
// inverter -> CD4013 toggle (SET preset) => exact 1 Hz, first rising edge t=1.000 s.
// Counter chain + MOD-6/MOD-24 self-reset decodes match sim/verify.js (25 h proven).
'use strict';

const F = 32768;                       // crystal Hz
const SEG = {0:'abcdef',1:'bc',2:'abdeg',3:'abcdg',4:'bcfg',5:'acdfg',6:'acdefg',7:'abc',8:'abcdefg',9:'abcdfg'};
const has = (n,s)=>SEG[n].indexOf(s)>=0;
const DIGS = ['SU','ST','MU','MT','HU','HT'];

function create(){
  const nets = {VCC:1, GND:0};
  const dig = {SU:0,ST:0,MU:0,MT:0,HU:0,HT:0};
  let count=0, prevQ14=0;              // U1 CD4060 ripple divider
  let ff1=1, prevInv=1;                // U2 FF1 -> CLK1HZ (preset Q=1 during reset)
  let ff2=0, prevBtnSet=0;             // U2 FF2 -> SET_MODE (toggle on BTN_SET rise)
  let simTime=0;                       // seconds since power-on
  let porUntil=0.87;                   // POR pulse width (100k/10uF + Schmitt)
  let powered=true;
  const raw={SET:1,HOUR:1,MIN:1,SECRST:1,MSTRST:1};   // raw node: 1=released, 0=pressed
  const prevBtn={SET:0,HOUR:0,MIN:0,SECRST:0,MSTRST:0};
  const events=[];                     // {t, kind, net}
  const carryCount={secMin:0,minHour:0};

  function ev(kind,net){ events.push({t:simTime,kind,net}); if(events.length>4000) events.shift(); }

  // ---- combinational settle: evaluate every gate from current state ----
  function settle(){
    nets.CLK2HZ=prevQ14;
    nets.CLK2HZ_INV=1-prevQ14;
    nets.CLK1HZ=ff1;
    nets.FF1_D=1-ff1;
    nets.SET_MODE=ff2;
    nets.nSET_MODE=1-ff2;
    nets.FF2_D=1-ff2;
    for(const k in raw){ nets['BTN_'+k]=1-raw[k]; nets['BTN_'+k+'_n']=raw[k]; }
    nets.POR_N=(powered && simTime<porUntil)?0:1;
    nets.POR_RST=1-nets.POR_N;
    nets.RST_GLOBAL=nets.POR_RST | nets.BTN_MSTRST;
    nets.RST_SEC=nets.RST_GLOBAL | nets.BTN_SECRST;
    // CD4026 segment outputs (a..g) per digit
    for(const d of DIGS){ const s=SEG[dig[d]];
      for(const seg of 'abcdefg') nets['SEG_'+d+'_'+seg.toUpperCase()]=has(dig[d],seg)?1:0;
      for(const seg of 'abcdefg') nets['DSP_'+d+'_'+seg.toUpperCase()]=nets['SEG_'+d+'_'+seg.toUpperCase()];
    }
    // U9 ANDs: MOD-6 tens decodes (e.f.g)
    nets.ST_EF=nets.SEG_ST_E & nets.SEG_ST_F; nets.D6_ST=nets.ST_EF & nets.SEG_ST_G;
    nets.MT_EF=nets.SEG_MT_E & nets.SEG_MT_F; nets.D6_MT=nets.MT_EF & nets.SEG_MT_G;
    // U10 ANDs: hour tens=2 (a.d.g), hour units=4 (c.f.g)
    nets.HT_AD=nets.SEG_HT_A & nets.SEG_HT_D; nets.HT2=nets.HT_AD & nets.SEG_HT_G;
    nets.HU_CF=nets.SEG_HU_C & nets.SEG_HU_F; nets.HU4=nets.HU_CF & nets.SEG_HU_G;
    nets.D24=nets.HT2 & nets.HU4;                       // U11/1
    // U12 ORs: reset combining
    nets.RST_ST=nets.RST_SEC | nets.D6_ST;
    nets.RST_MT=nets.RST_GLOBAL | nets.D6_MT;
    nets.RST_HOURS=nets.RST_GLOBAL | nets.D24;
    // U11 clock gating
    nets.CLK_SEC=nets.CLK1HZ & nets.nSET_MODE;
    nets.HOUR_GATE=nets.BTN_HOUR & nets.SET_MODE;
    nets.MIN_GATE=nets.BTN_MIN & nets.SET_MODE;
    // U13 ORs: carry/manual clock combining
    nets.CLK_MU=nets.D6_ST | nets.MIN_GATE;
    nets.CLK_HU=nets.D6_MT | nets.HOUR_GATE;
    // CD4026 carry-out levels (high counts 0..4; rising edge at 9->0 clocks next)
    nets.C_SU=dig.SU<=4?1:0; nets.C_MU=dig.MU<=4?1:0; nets.C_HU=dig.HU<=4?1:0;
    // colon driver Q1: base=CLK1HZ, saturated => COLON_K low => LEDs lit
    nets.COLON_B=nets.CLK1HZ; nets.COLON_K=nets.CLK1HZ?0:1;
    nets.COLON_A1=1; nets.COLON_A2=1;
  }

  // ---- sequential counter chain (identical semantics to verify.js) ----
  function clockHT(){ dig.HT++; ev('clk','C_HU'); }
  function clockHU(){ dig.HU++;
    if(dig.HT===2 && dig.HU===4){ dig.HU=0; dig.HT=0; ev('reset24','D24'); return; }
    if(dig.HU===10){ dig.HU=0; clockHT(); } }
  function clockMT(){ dig.MT++; if(dig.MT===6){ dig.MT=0; carryCount.minHour++; ev('carry','D6_MT'); clockHU(); } }
  function clockMU(){ dig.MU++; if(dig.MU===10){ dig.MU=0; clockMT(); } }
  function clockST(){ dig.ST++; if(dig.ST===6){ dig.ST=0; carryCount.secMin++; ev('carry','D6_ST'); clockMU(); } }
  function clockSU(){ dig.SU++; if(dig.SU===10){ dig.SU=0; clockST(); } }

  function holdReset(){ count=0; prevQ14=0; ff1=1; prevInv=1; ff2=0; prevBtnSet=0;
    for(const d of DIGS) dig[d]=0; }

  function applyResets(){
    if(nets.RST_GLOBAL) holdReset();
    if(nets.RST_SEC){ dig.SU=0; dig.ST=0; }
    if(nets.RST_ST) dig.ST=0;
    if(nets.RST_MT) dig.MT=0;
    if(nets.RST_HOURS){ dig.HU=0; dig.HT=0; }
  }

  // ---- timebase: one CD4060 count per crystal edge; act only on Q14 transitions ----
  function onQ14(){
    const inv=1-prevQ14;
    if(inv===1 && prevInv===0){          // rising edge of FF1 clock (CLK2HZ_INV)
      ff1=1-ff1;                         // toggle (D=Q/)
      if(ff1===1){ ev('clk','CLK1HZ'); if(!ff2) clockSU(); }  // CLK_SEC gated by nSET_MODE
    }
    prevInv=inv;
  }

  function step(dt){
    if(!powered) return;
    simTime+=dt;
    settle();
    if(nets.RST_GLOBAL){ holdReset(); }
    else {
      let cycles=Math.round(dt*F);
      for(let i=0;i<cycles;i++){
        count++;
        const q14=(count>>13)&1;
        if(q14!==prevQ14){ prevQ14=q14; onQ14(); }
      }
    }
    applyResets();
    settle();
  }

  // ---- buttons (clean UI press; hardware RC+Schmitt debounce present in netlist) ----
  function buttonEdge(k){
    const b=1-raw[k];
    if(b===1 && prevBtn[k]===0){
      if(k==='SET'){ ff2=1-ff2; ev('set','BTN_SET'); }
      else if(k==='HOUR'){ if(ff2) clockHU(); }
      else if(k==='MIN'){ if(ff2) clockMU(); }
    }
    prevBtn[k]=b;
  }
  function press(k){ raw[k]=0; settle(); buttonEdge(k); applyResets(); settle(); }
  function release(k){ raw[k]=1; settle(); buttonEdge(k); applyResets(); settle(); }

  function powerCycle(){ powered=false; }
  function powerOn(){ powered=true; simTime=0; porUntil=0.87; holdReset(); events.length=0;
    carryCount.secMin=0; carryCount.minHour=0; settle(); }

  function display(){ const p=n=>String(n).padStart(2,'0');
    return p(dig.HT*10+dig.HU)+':'+p(dig.MT*10+dig.MU)+':'+p(dig.ST*10+dig.SU); }

  settle();
  return {nets,dig,events,carryCount,step,press,release,powerCycle,powerOn,display,
    get simTime(){return simTime;}, get setMode(){return !!ff2;}, get powered(){return powered;},
    get colon(){return nets.COLON_K===0;}};
}

const api={create,F,SEG,DIGS};
if(typeof module!=='undefined' && module.exports) module.exports=api;
else window.ClockEngine=api;