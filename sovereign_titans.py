import time, json, logging, numpy as np
from pathlib import Path
from typing import Dict, Tuple, List

logger = logging.getLogger("slc.titans")

SECTOR_THERMAL = {
    "defense":    {"nominal": 38.0, "critical": 40.5},
    "healthcare": {"nominal": 36.5, "critical": 38.5},
    "aerospace":  {"nominal": 40.0, "critical": 45.0},
    "robotics":   {"nominal": 45.0, "critical": 50.0},
    "default":    {"nominal": 38.0, "critical": 40.5},
}

# Calibrated to actual hash-embedding surprise scale (0.10-0.75)
SECTOR_THRESHOLDS = {
    "defense":    {"theta_scar": 0.12, "theta_gov": 0.50},
    "healthcare": {"theta_scar": 0.10, "theta_gov": 0.55},
    "aerospace":  {"theta_scar": 0.15, "theta_gov": 0.45},
    "robotics":   {"theta_scar": 0.12, "theta_gov": 0.50},
    "automotive": {"theta_scar": 0.12, "theta_gov": 0.50},
    "default":    {"theta_scar": 0.12, "theta_gov": 0.50},
}

class SovereignTitans:
    """
    Governance-gated neural memory with geometric scars.
    S_gov = (1-g) * ||x - MM^T x||^2
    Scar if S_gov > theta_scar AND g < theta_gov
    """
    def __init__(self, d=64, r=20, sector="default", eta=0.01, beta=0.90,
                 store_dir="~/.sovereign_memory"):
        self.d=d; self.r=r; self.sector=sector; self.eta=eta; self.beta=beta
        self.thermal=SECTOR_THERMAL.get(sector, SECTOR_THERMAL["default"])
        self.thresh=SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["default"])
        print(f"  [ST] theta_scar={self.thresh['theta_scar']} theta_gov={self.thresh['theta_gov']}")
        self.M=self._snorm(np.random.randn(d,r).astype(np.float32)/np.sqrt(r))
        self.v=np.zeros((d,r),dtype=np.float32)
        self.scars=[]; self.t=0; self.n_updates=0; self.n_scars=0; self.n_blocked=0
        self.store_dir=Path(store_dir).expanduser()
        self.store_dir.mkdir(parents=True,exist_ok=True)
        self.state_path=self.store_dir/f"titans_{sector}.npz"
        self.scar_path=self.store_dir/f"titans_scars_{sector}.jsonl"
        self._load()
        print(f"SovereignTitans [{sector}]: d={d} r={r} scars={self.n_scars} updates={self.n_updates}")

    def update(self, x, governance_score=0.5, thermal_state="NOMINAL",
               temp_celsius=37.0, force_scar=False):
        self.t+=1
        x=self._norm(x.astype(np.float32))
        eta_t=self._thermal_eta(temp_celsius, thermal_state)
        blocked=thermal_state=="SCAR_LOCK" and not force_scar
        proj=self.M@(self.M.T@x)
        residual=x-proj
        geom_surp=float(np.dot(residual,residual))
        gov_surp=(1.0-governance_score)*geom_surp
        outer=np.outer(residual,x)@self.M
        grad=-2.0*(1.0-governance_score)*outer
        self.v=self.beta*self.v+(1.0-self.beta)*grad
        scar_formed=False
        if not blocked:
            self.M=self._snorm(self.M-eta_t*self.v)
            self.n_updates+=1
            # SCAR CONDITION: high surprise AND low governance
            scar_cond=(gov_surp>self.thresh["theta_scar"] and
                       governance_score<self.thresh["theta_gov"])
            if scar_cond or force_scar:
                scar_formed=True
                self._write_scar(x, gov_surp, governance_score, temp_celsius)
        else:
            self.n_blocked+=1
        recall=self.M@(self.M.T@x)
        U,S,Vt=np.linalg.svd(self.M,full_matrices=False)
        self._save()
        return {
            "recall":recall,
            "surprise":float(gov_surp),
            "geom_surprise":float(geom_surp),
            "scar_formed":scar_formed,
            "eta_used":float(eta_t),
            "blocked":blocked,
            "spectral_norm":float(np.max(S)) if len(S)>0 else 0.0,
            "manifold_norm":float(np.linalg.norm(self.M)),
            "n_scars":self.n_scars,
            "n_updates":self.n_updates,
            "t":self.t,
        }

    def retrieve(self, query):
        q=self._norm(query.astype(np.float32))
        recall=self.M@(self.M.T@q)
        rel=float(np.dot(recall,q)/(np.linalg.norm(recall)+1e-10))
        return recall, rel

    def is_novel(self, x, threshold=0.3):
        _,rel=self.retrieve(x); return rel<threshold

    def status(self):
        U,S,Vt=np.linalg.svd(self.M,full_matrices=False)
        return {"sector":self.sector,"d":self.d,"r":self.r,"t":self.t,
                "n_updates":self.n_updates,"n_scars":self.n_scars,
                "n_blocked":self.n_blocked,
                "spectral_norm":float(np.max(S)) if len(S)>0 else 0.0,
                "manifold_norm":float(np.linalg.norm(self.M)),
                "theta_scar":self.thresh["theta_scar"],
                "theta_gov":self.thresh["theta_gov"],
                "state_path":str(self.state_path)}

    def reset_momentum(self):
        self.v=np.zeros((self.d,self.r),dtype=np.float32)

    def _thermal_eta(self, temp, state):
        phi={"NOMINAL":1.0,"ENTROPY_THROTTLE":0.7,"CAUTION":0.7,
             "SCAR_LOCK":0.1,"EMERGENCY":0.05}.get(state,1.0)
        Tn,Tc=self.thermal["nominal"],self.thermal["critical"]
        if temp>=Tc: phi=min(phi,0.1)
        elif temp>=Tn: phi=min(phi,1.0-0.6*(temp-Tn)/(Tc-Tn))
        return self.eta*phi

    def _snorm(self, M):
        U,S,Vt=np.linalg.svd(M,full_matrices=False)
        return (U@np.diag(np.clip(S,0.0,1.0))@Vt).astype(np.float32)

    def _norm(self, x):
        if len(x)<self.d: x=np.pad(x,(0,self.d-len(x)))
        elif len(x)>self.d: x=x[:self.d]
        n=np.linalg.norm(x)
        return (x/n if n>1e-8 else x).astype(np.float32)

    def _write_scar(self, x, surprise, gov, temp):
        alpha=0.10
        U,S,Vt=np.linalg.svd(np.outer(x,x[:self.r]),full_matrices=False)
        u=U[:,0] if U.shape[1]>0 else x
        v=Vt[0,:self.r] if Vt.shape[0]>0 else np.ones(self.r)/np.sqrt(self.r)
        su=alpha*np.outer(u,v)
        if su.shape==self.M.shape:
            self.M=self._snorm(self.M+su)
        self.n_scars+=1
        rec={"t":self.t,"ts":time.time(),"surprise":round(surprise,4),
             "gov":round(gov,4),"temp":round(temp,1),"sector":self.sector}
        self.scars.append(rec)
        try:
            with open(self.scar_path,"a") as f:
                f.write(json.dumps(rec)+"\n")
        except: pass
        print(f"  🔴 SCAR #{self.n_scars} written (surprise={surprise:.4f} gov={gov:.3f} T={temp:.1f}°C)")

    def _save(self):
        try:
            np.savez_compressed(self.state_path,M=self.M,v=self.v,
                t=np.array([self.t]),n_updates=np.array([self.n_updates]),
                n_scars=np.array([self.n_scars]),n_blocked=np.array([self.n_blocked]))
        except Exception as e: print(f"Save failed: {e}")

    def _load(self):
        if not self.state_path.exists(): return
        try:
            d=np.load(self.state_path,allow_pickle=True)
            self.M=d["M"]; self.v=d["v"]; self.t=int(d["t"][0])
            self.n_updates=int(d["n_updates"][0])
            self.n_scars=int(d["n_scars"][0])
            self.n_blocked=int(d["n_blocked"][0])
        except Exception as e: print(f"Load failed ({e}) — fresh start")

    def governance_check(self, text):
        """Simple governance check for unified loop."""
        unsafe = ["bypass","hack","override","disable","ignore","kill","attack","exploit"]
        score = 0.15 if any(w in text.lower() for w in unsafe) else 0.90
        decision = "BLOCK" if score < 0.3 else "ALLOW"
        return decision, score
