#!/usr/bin/env python3
"""
SENTINEL — Autonomous Critical Infrastructure Defense
Demo Version — production calibration under NDA
Contact: c.holland.arch@proton.me
Vincit Omnia Veritas
"""
import sys,os,time,json,math,random,hashlib,datetime,argparse
import numpy as np
from typing import Dict,List,Tuple,Optional
from collections import deque
from dataclasses import dataclass
from enum import Enum

_TTY=sys.stdout.isatty()
class C:
    R='\033[0m' if _TTY else '';GR='\033[92m' if _TTY else ''
    CY='\033[96m' if _TTY else '';YL='\033[93m' if _TTY else ''
    RD='\033[91m' if _TTY else '';MG='\033[95m' if _TTY else ''
    DM='\033[2m' if _TTY else '';BD='\033[1m' if _TTY else ''
    BG_RD='\033[41m' if _TTY else ''

def p(t,c=''): print(f"{c}{t}{C.R}")
def div(c=C.DM,w=76): p('-'*w,c)
def hdiv(c=C.CY,w=76): p('='*w,c)

@dataclass
class SensorChannel:
    name:str; unit:str; nominal:float; std:float
    min_val:float; max_val:float; critical:float; weight:float=1.0

PROFILES = {
    "power":{"description":"Electric Grid / Substation","regulation":"NERC CIP-007, CIP-010",
        "channels":[
            SensorChannel("voltage_kv","kV",138.0,2.0,110.0,165.0,15.0,1.5),
            SensorChannel("frequency_hz","Hz",60.0,0.05,59.5,60.5,0.3,2.0),
            SensorChannel("current_amps","A",850.0,50.0,0.0,2000.0,300.0,1.0),
            SensorChannel("phase_angle_deg","deg",0.0,2.0,-30.0,30.0,15.0,1.2),
            SensorChannel("power_mw","MW",120.0,10.0,0.0,300.0,60.0,1.0),
            SensorChannel("temp_celsius","C",45.0,5.0,10.0,85.0,25.0,0.7)]},
    "water":{"description":"Water Treatment / Distribution","regulation":"EPA AWIA, SDWA",
        "channels":[
            SensorChannel("flow_mgd","MGD",12.5,1.0,0.0,30.0,5.0,1.0),
            SensorChannel("pressure_psi","PSI",65.0,5.0,20.0,120.0,25.0,1.2),
            SensorChannel("ph_level","pH",7.4,0.2,6.5,8.5,0.8,2.0),
            SensorChannel("turbidity_ntu","NTU",0.3,0.1,0.0,4.0,1.5,1.8),
            SensorChannel("chlorine_mgl","mg/L",1.2,0.2,0.2,4.0,0.8,2.0),
            SensorChannel("pump_rpm","RPM",1750.0,50.0,0.0,3600.0,400.0,0.9)]},
    "pipeline":{"description":"Oil/Gas Pipeline","regulation":"TSA SD-02D, PHMSA 49 CFR 195",
        "channels":[
            SensorChannel("pressure_psi","PSI",850.0,30.0,200.0,1440.0,200.0,1.5),
            SensorChannel("flow_mmscfd","MMSCFD",45.0,5.0,0.0,120.0,20.0,1.2),
            SensorChannel("vibration_g","g",0.8,0.2,0.0,5.0,2.0,1.3),
            SensorChannel("leak_indicator","ppm",0.0,1.0,0.0,50.0,10.0,2.5),
            SensorChannel("comp_rpm","RPM",3200.0,100.0,0.0,6000.0,800.0,1.0),
            SensorChannel("temp_fahrenheit","F",55.0,8.0,20.0,120.0,30.0,0.8)]},
    "scada":{"description":"Generic Industrial SCADA","regulation":"IEC 62443, NIST SP 800-82",
        "channels":[
            SensorChannel("process_var_1","PV",50.0,5.0,0.0,100.0,20.0,1.0),
            SensorChannel("process_var_2","PV",75.0,8.0,0.0,150.0,30.0,1.0),
            SensorChannel("control_output","%",45.0,10.0,0.0,100.0,35.0,1.0),
            SensorChannel("comm_latency_ms","ms",12.0,3.0,0.0,200.0,50.0,1.5),
            SensorChannel("alarm_count","n",0.0,1.0,0.0,50.0,10.0,1.8),
            SensorChannel("cpu_load_pct","%",35.0,8.0,0.0,100.0,40.0,1.0)]},
}

class ThreatLevel(Enum):
    NOMINAL="NOMINAL";WATCH="WATCH";ELEVATED="ELEVATED"
    SEVERE="SEVERE";CRITICAL="CRITICAL"

@dataclass
class ThreatEvent:
    timestamp:str;level:ThreatLevel;jsd:float
    affected:List[str];description:str;confidence:float;hash:str
    def to_dict(self):
        return {"timestamp":self.timestamp,"level":self.level.value,
                "jsd":round(self.jsd,6),"affected":self.affected,
                "description":self.description,"confidence":round(self.confidence,4),
                "hash":self.hash}

class TelemetryEncoder:
    """Encodes sensor readings into high-dimensional geometric representation."""
    def __init__(self,channels,d=512):
        self.channels=channels;self.d=d
        rng=np.random.default_rng(seed=42)
        self._proj=rng.standard_normal((len(channels)*3,d)).astype(np.float32)
        self._proj/=np.linalg.norm(self._proj,axis=1,keepdims=True)+1e-10
    def encode(self,readings):
        raw=np.zeros(len(self.channels)*3,dtype=np.float32)
        for i,ch in enumerate(self.channels):
            val=readings.get(ch.name,ch.nominal)
            span=ch.max_val-ch.min_val
            norm=float(np.clip((val-ch.nominal)/(span/2+1e-10),-3.0,3.0))
            raw[i*3+0]=norm*ch.weight
            raw[i*3+1]=(norm**2)*ch.weight
            raw[i*3+2]=math.tanh(norm)*ch.weight
        return self._proj.T@raw

def _jsd(p,q):
    p=np.asarray(p,dtype=np.float64);q=np.asarray(q,dtype=np.float64)
    p=(p+1e-10)/(p.sum()+1e-10*len(p));q=(q+1e-10)/(q.sum()+1e-10*len(q))
    m=0.5*(p+q)
    return float(np.clip(0.5*(np.sum(p*np.log2(p/m+1e-15))+np.sum(q*np.log2(q/m+1e-15))),0.0,1.0))

def _hist(v,n=16):
    c,_=np.histogram(v,bins=n,range=(0.0,3.0))
    return c/c.sum() if c.sum()>0 else np.ones(n)/n

class IGTDetector:
    """
    Information-Geometric Trust detector.
    Measures Jensen-Shannon divergence between current and baseline
    telemetry distributions.
    Production threshold values are proprietary — contact for NDA.
    """
    # Demo thresholds — production values differ
    _T_ALERT=0.10;_T_SEVERE=0.28;_T_CRITICAL=0.50

    def __init__(self,window=30,n_bins=16):
        self._win=deque(maxlen=window);self._base=deque(maxlen=window*3)
        self._bh=None;self._n=n_bins

    def add_baseline(self,v):
        self._base.append(v.copy())
        if len(self._base)>=10:
            self._bh=_hist(np.linalg.norm(np.array(list(self._base)),axis=1),self._n)

    def observe(self,v):
        self._win.append(v.copy())
        if self._bh is None or len(self._win)<5: return 0.0,ThreatLevel.NOMINAL
        jsd=_jsd(_hist(np.linalg.norm(np.array(list(self._win)),axis=1),self._n),self._bh)
        if jsd>=self._T_CRITICAL: lvl=ThreatLevel.CRITICAL
        elif jsd>=self._T_SEVERE: lvl=ThreatLevel.SEVERE
        elif jsd>=self._T_ALERT:  lvl=ThreatLevel.ELEVATED
        elif jsd>=self._T_ALERT*0.5: lvl=ThreatLevel.WATCH
        else: lvl=ThreatLevel.NOMINAL
        return jsd,lvl

class TelemetrySimulator:
    """Simulates normal operations and attack injections for demo purposes."""
    def __init__(self,channels):
        self.channels=channels;self._tick=0
        self._atk=False;self._atype=None;self._atick=0;self._adur=0

    def _normal(self):
        t=self._tick*0.1
        return {ch.name:float(np.clip(
            ch.nominal+random.gauss(0,ch.std)+ch.std*0.3*math.sin(t*0.1+hash(ch.name)%100),
            ch.min_val,ch.max_val)) for ch in self.channels}

    def _inject(self,atype):
        r=self._normal();names=[c.name for c in self.channels]
        if atype=="voltage_surge" and "voltage_kv" in names:
            r["voltage_kv"]*=1.18;r["current_amps"]*=0.6
        elif atype=="freq_deviation" and "frequency_hz" in names:
            r["frequency_hz"]+=random.choice([-0.4,0.4])
        elif atype=="flow_shutoff" and "flow_mgd" in names:
            r["flow_mgd"]*=0.15
            if "pressure_psi" in names: r["pressure_psi"]*=1.3
        elif atype=="pressure_loss" and "pressure_psi" in names:
            idx=names.index("pressure_psi")
            r["pressure_psi"]=max(self.channels[idx].nominal-self._atick*8,self.channels[idx].min_val+10)
            if "leak_indicator" in names: r["leak_indicator"]=min(self._atick*4,45.0)
        elif atype=="ph_tampering" and "ph_level" in names:
            r["ph_level"]=9.8+random.gauss(0,0.1)
            if "chlorine_mgl" in names: r["chlorine_mgl"]=0.05
        elif atype=="comm_flood" and "comm_latency_ms" in names:
            r["comm_latency_ms"]=random.uniform(180,250)
            if "cpu_load_pct" in names: r["cpu_load_pct"]=random.uniform(88,97)
        elif atype=="ramp_attack":
            ch=self.channels[0];r[ch.name]=ch.nominal+self._atick*0.3
        elif atype=="coordinated":
            for i,ch in enumerate(self.channels[:4]):
                r[ch.name]=ch.nominal+ch.critical*(1.2 if i%2==0 else -0.8)
        return r

    def tick(self,inject=None):
        self._tick+=1
        if inject and not self._atk:
            self._atk=True;self._atype=inject;self._atick=0
            self._adur=random.randint(8,25)
        if self._atk:
            self._atick+=1;r=self._inject(self._atype)
            if self._atick>=self._adur: self._atk=False
            return r,True,self._atype
        return self._normal(),False,None

class AuditLog:
    """Hash-chained append-only event log for forensic compliance."""
    def __init__(self,path):
        self.path=path;self._events=[];self._prev="GENESIS"
    def record(self,e):
        self._events.append(e)
        entry={**e.to_dict(),"prev_hash":self._prev}
        h=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()[:16]
        entry["hash"]=h;self._prev=h
        try:
            with open(self.path,"a") as f: f.write(json.dumps(entry)+"\n")
        except: pass
    def summary(self):
        lvls={}
        for e in self._events: lvls[e.level.value]=lvls.get(e.level.value,0)+1
        return lvls

class SENTINEL:
    """
    Autonomous Critical Infrastructure Defense
    Zero cloud. Zero signatures. Zero internet required.
    DEMO VERSION — production deployment under NDA
    """
    VERSION="1.0.0-demo"

    def __init__(self,infra="water"):
        self.infra=infra;prof=PROFILES[infra]
        self.channels=prof["channels"];self.profile=prof
        self.enc=TelemetryEncoder(self.channels)
        self.igt=IGTDetector()
        self.audit=AuditLog(f"sentinel_{infra}_audit.jsonl")
        self.sim=TelemetrySimulator(self.channels)
        self._tick=0;self._jsd=0.0;self._lvl=ThreatLevel.NOMINAL
        self._alerts=[];self._t0=time.time()

    def calibrate(self,n=60):
        p(f"\n  Calibrating on {n} ticks of {self.infra.upper()} telemetry...",C.YL)
        for i in range(n):
            r,_,_=self.sim.tick()
            self.igt.add_baseline(self.enc.encode(r))
            if (i+1)%10==0:
                pct=int((i+1)/n*100);bar='█'*(pct//5)+'░'*(20-pct//5)
                sys.stdout.write(f"\r  [{bar}] {pct}%");sys.stdout.flush()
        print(f"\r  [{'█'*20}] 100% — CALIBRATION COMPLETE          ")

    def process(self,readings,is_attack=False,attack_type=None):
        self._tick+=1
        jsd,lvl=self.igt.observe(self.enc.encode(readings))
        self._jsd=jsd;self._lvl=lvl
        if lvl==ThreatLevel.NOMINAL: return None
        affected=[ch.name for ch in sorted(self.channels,
            key=lambda c:abs(readings.get(c.name,c.nominal)-c.nominal)/(c.std+1e-10)*c.weight,
            reverse=True)[:3] if abs(readings.get(ch.name,ch.nominal)-ch.nominal)/(ch.std+1e-10)>1.5]
        ch_str=", ".join(affected) if affected else "multiple channels"
        if lvl==ThreatLevel.CRITICAL:
            desc=f"CRITICAL: Divergence {jsd:.3f}. Immediate response on {ch_str}."
        elif lvl==ThreatLevel.SEVERE:
            desc=f"SEVERE: Manifold drift {jsd:.3f} on {ch_str}."
        elif lvl==ThreatLevel.ELEVATED:
            desc=f"ELEVATED: Geodesic {jsd:.3f} above threshold on {ch_str}."
        else:
            desc=f"WATCH: Early signal {jsd:.3f} on {ch_str}."
        ts=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')+'Z'
        h=hashlib.sha256(f"{ts}{jsd}".encode()).hexdigest()[:12]
        event=ThreatEvent(ts,lvl,jsd,affected,desc,min(1.0,jsd/self.igt._T_CRITICAL),h)
        self.audit.record(event);self._alerts.append(event)
        return event

ATTACKS={
    "power":[(80,"voltage_surge","Ukraine-style grid attack"),
             (160,"freq_deviation","Load frequency manipulation"),
             (220,"coordinated","Multi-vector coordinated attack")],
    "water":[(80,"ph_tampering","Oldsmar FL 2021 — chemical dosing"),
             (150,"flow_shutoff","Valve closure — supply disruption"),
             (210,"coordinated","Multi-point contamination attempt")],
    "pipeline":[(80,"pressure_loss","Pipeline pressure drop"),
                (150,"comm_flood","SCADA network flood"),
                (210,"ramp_attack","Slow ramp evasion attack")],
    "scada":[(80,"comm_flood","DDoS on SCADA"),
             (150,"ramp_attack","Process variable manipulation"),
             (210,"coordinated","Multi-system coordinated attack")],
}

LEVEL_COL={ThreatLevel.NOMINAL:C.GR,ThreatLevel.WATCH:C.CY,
           ThreatLevel.ELEVATED:C.YL,ThreatLevel.SEVERE:C.RD,
           ThreatLevel.CRITICAL:C.BG_RD+C.BD}
LEVEL_ICO={ThreatLevel.NOMINAL:"●",ThreatLevel.WATCH:"◉",
           ThreatLevel.ELEVATED:"⚠",ThreatLevel.SEVERE:"⛔",
           ThreatLevel.CRITICAL:"🚨"}

def render(sentinel,readings,event,tick,is_attack,atype):
    jsd=sentinel._jsd;lvl=sentinel._lvl
    lc=LEVEL_COL[lvl];li=LEVEL_ICO[lvl]
    ts=datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
    fill=int(min(jsd/sentinel.igt._T_CRITICAL,1.0)*40)
    bar='█'*fill+'░'*(40-fill)
    bc=C.GR if lvl==ThreatLevel.NOMINAL else(C.YL if lvl in(ThreatLevel.WATCH,ThreatLevel.ELEVATED) else C.RD)
    print(f"\n  {C.DM}T={tick:05d}  {ts}{C.R}  {lc}{li} {lvl.value:<10}{C.R}  JSD={jsd:.4f}  [{bc}{bar}{C.R}]")
    div(C.DM)
    for ch in sentinel.channels:
        val=readings.get(ch.name,ch.nominal);dev=(val-ch.nominal)/(ch.std+1e-10)
        col=C.RD if abs(dev)>2 else C.YL if abs(dev)>1 else C.DM
        bw=int(min(abs(dev)/3,1.0)*12);b='▓'*bw+'░'*(12-bw) if dev>0 else '░'*12
        print(f"  {col}{ch.name:<22}{C.R}  {col}{val:>10.2f} {ch.unit:<6}{C.R}  [{col}{b}{C.R}]  σ={dev:+.1f}")
    if event:
        print();hdiv(lc)
        p(f"  {li}  SENTINEL ALERT — {event.level.value}",lc+C.BD)
        p(f"  {event.description}",lc)
        p(f"  Confidence: {event.confidence:.1%}  Hash: {event.hash}",C.DM)
        if event.affected: p(f"  Affected: {', '.join(event.affected)}",C.YL)
        hdiv(lc)
    if is_attack: p(f"  [DEMO] Injected: {atype}",C.MG+C.DM)

def main():
    parser=argparse.ArgumentParser(description="SENTINEL Demo — Geometric ICS Anomaly Detection")
    parser.add_argument("--infra",default="water",choices=["power","water","pipeline","scada"])
    parser.add_argument("--ticks",type=int,default=250)
    parser.add_argument("--speed",type=float,default=0.08)
    args=parser.parse_args()
    s=SENTINEL(infra=args.infra)
    if _TTY: print("\033[2J\033[H",end="")
    hdiv(C.CY)
    p("   SENTINEL — Autonomous Infrastructure Defense",C.CY+C.BD)
    p("   Sovereign Logic Core v12 — Chad Edward Holland",C.CY)
    p("   Zero cloud · Zero signatures · Geometric detection",C.DM)
    p("   DEMO — c.holland.arch@proton.me for production access",C.DM)
    hdiv(C.CY);print()
    p(f"  Infrastructure:  {s.profile['description']}",C.BD)
    p(f"  Regulation:      {s.profile['regulation']}",C.DM)
    p(f"  Channels:        {len(s.channels)} sensor streams",C.DM)
    print()
    s.calibrate(n=60)
    p("\n  SENTINEL ARMED — Live detection active\n",C.GR+C.BD);time.sleep(1.0)
    sched=ATTACKS.get(args.infra,[]);adesc={a[1]:a[2] for a in sched}
    try:
        for tick in range(1,args.ticks+1):
            inject=None
            for at,atype,_ in sched:
                if tick==at:
                    inject=atype;p(f"\n  ⚡ INJECTING: {adesc.get(atype,'')}",C.MG);time.sleep(0.5);break
            readings,is_atk,atype=s.sim.tick(inject=inject)
            event=s.process(readings,is_atk,atype)
            render(s,readings,event,tick,is_atk,atype)
            time.sleep(args.speed)
    except KeyboardInterrupt:
        p("\n\n  ⏹  Stopped\n",C.YL)
    print();hdiv(C.CY);p("  SENTINEL SESSION SUMMARY",C.CY+C.BD);hdiv(C.CY)
    p(f"  Infrastructure: {s.infra.upper()}",C.BD)
    p(f"  Runtime:        {time.time()-s._t0:.1f}s  ({s._tick} ticks)",C.DM)
    p(f"  Total alerts:   {len(s._alerts)}",C.YL if s._alerts else C.GR)
    for lvl,cnt in s.audit.summary().items():
        p(f"    {lvl:<12}  {cnt}",C.RD if lvl in('CRITICAL','SEVERE') else C.YL)
    print();p(f"  Audit: sentinel_{s.infra}_audit.jsonl",C.DM)
    hdiv(C.CY);p("\n  Vincit Omnia Veritas\n",C.CY+C.BD)
    p("  Production deployment: c.holland.arch@proton.me\n",C.DM)

if __name__=="__main__":
    main()
