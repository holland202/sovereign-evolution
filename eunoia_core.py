import time,json,hashlib,logging,numpy as np
from pathlib import Path
logger=logging.getLogger("sovereign.eunoia")
THERMAL_ZONES=["/sys/class/thermal/thermal_zone0/temp","/sys/class/thermal/thermal_zone4/temp"]
THERMAL_PHI={"NOMINAL":1.0,"CAUTION":0.7,"THROTTLE":0.4,"SCAR_LOCK":0.05}
def read_device_temp():
    temps=[]
    for path in THERMAL_ZONES:
        try:
            with open(path) as f:
                t=int(f.read().strip())/1000.0
                if 0<t<120: temps.append(t)
        except: pass
    temp=max(temps) if temps else 37.0
    if temp>=40.5: state="SCAR_LOCK"
    elif temp>=38.5: state="THROTTLE"
    elif temp>=37.0: state="CAUTION"
    else: state="NOMINAL"
    return temp,state
class EunoiaThought:
    def __init__(self,input_text,thought_vec,residual,understanding,coherence,is_insight,thermal_state,temp,t):
        self.input_text=input_text;self.thought_vec=thought_vec;self.residual=residual
        self.understanding=understanding;self.coherence=coherence;self.is_insight=is_insight
        self.thermal_state=thermal_state;self.temp=temp;self.t=t
    def is_known(self): return self.understanding>0.6
    def is_uncertain(self): return self.understanding<0.4
    def narrate(self):
        if self.is_insight: return f"[INSIGHT] Understanding jumped to {self.understanding:.0%}. Geometry permanently changed."
        elif self.is_known(): return f"[KNOWN] I understand this well ({self.understanding:.0%}). Coherence: {self.coherence:.3f}."
        elif self.is_uncertain(): return f"[UNCERTAIN] I don't understand this well ({self.understanding:.0%}). Be cautious."
        else: return f"[PARTIAL] I partially understand this ({self.understanding:.0%})."
class Eunoia:
    def __init__(self,d=128,r=32,eta=0.008,beta=0.90,sigma=0.5,insight_threshold=0.35,store_dir="~/.sovereign_memory"):
        self.d=d;self.r=r;self.eta=eta;self.beta=beta;self.sigma=sigma
        self.insight_threshold=insight_threshold
        self.C=self._snorm(np.random.randn(d,r).astype(np.float32)/np.sqrt(r))
        self.v=np.zeros((d,r),dtype=np.float32)
        self.t=0;self.n_thoughts=0;self.n_insights=0;self.n_blocked=0
        self.scars=[]
        self.store_dir=Path(store_dir).expanduser()
        self.store_dir.mkdir(parents=True,exist_ok=True)
        self.state_path=self.store_dir/"eunoia_coherence.npz"
        self.scar_path=self.store_dir/"eunoia_scars.jsonl"
        self._load()
        print(f"Eunoia: d={d}, r={r}, thoughts={self.n_thoughts}, insights={self.n_insights}")
    def think(self,text,context=None,governance=0.8,force_update=False):
        self.t+=1;self.n_thoughts+=1
        temp,thermal_state=read_device_temp()
        eta_t=self.eta*THERMAL_PHI.get(thermal_state,1.0)
        blocked=thermal_state=="SCAR_LOCK" and not force_update
        x=self._embed(f"{context} {text}" if context else text)
        proj_before=self.C@(self.C.T@x);res_before=x-proj_before
        u_before=self._understanding(x,res_before)
        coherence=float(np.exp(-np.dot(res_before,res_before)/(self.sigma**2)))
        res_norm=res_before/(np.linalg.norm(res_before)+1e-10)
        thought_vec=u_before*proj_before+(1-u_before)*res_norm
        is_insight=False
        if not blocked:
            grad=-2.0*governance*np.outer(res_before,x)@self.C
            self.v=self.beta*self.v+(1.0-self.beta)*grad
            self.C=self._snorm(self.C-eta_t*self.v)
            proj_after=self.C@(self.C.T@x);res_after=x-proj_after
            u_after=self._understanding(x,res_after);delta_u=u_after-u_before
            if delta_u>self.insight_threshold and u_before<0.5:
                is_insight=True;self.n_insights+=1
                self._write_scar(x,u_before,u_after,delta_u,text,temp)
        else:
            self.n_blocked+=1
        thought=EunoiaThought(text,thought_vec,res_before,float(u_before),float(coherence),is_insight,thermal_state,temp,self.t)
        self._save()
        return thought
    def understand(self,text):
        x=self._embed(text);proj=self.C@(self.C.T@x);res=x-proj
        return float(self._understanding(x,res))
    def compare(self,text_a,text_b):
        xa=self._embed(text_a);xb=self._embed(text_b)
        proj_a=self.C@(self.C.T@xa);proj_b=self.C@(self.C.T@xb)
        proj_sim=float(np.dot(proj_a,proj_b)/(np.linalg.norm(proj_a)*np.linalg.norm(proj_b)+1e-10))
        rel="strongly related" if proj_sim>0.8 else "related" if proj_sim>0.5 else "weakly related" if proj_sim>0.2 else "independent" if abs(proj_sim)<0.2 else "contradictory"
        return {"geometric_similarity":round(proj_sim,4),"relationship":rel}
    def status(self):
        U,S,Vt=np.linalg.svd(self.C,full_matrices=False)
        temp,thermal_state=read_device_temp()
        return {"d":self.d,"r":self.r,"t":self.t,"n_thoughts":self.n_thoughts,
                "n_insights":self.n_insights,"n_blocked":self.n_blocked,
                "spectral_norm":round(float(np.max(S)) if len(S)>0 else 0.0,6),
                "manifold_norm":round(float(np.linalg.norm(self.C)),6),
                "temp":round(temp,1),"thermal_state":thermal_state,"n_scars":len(self.scars)}
    def recent_insights(self,n=5): return self.scars[-n:]
    def _understanding(self,x,residual):
        xn=np.linalg.norm(x);rn=np.linalg.norm(residual)
        if xn<1e-10: return 0.0
        return float(max(0.0,1.0-rn/xn))
    def _embed(self,text):
        words=text.lower().split();vec=np.zeros(self.d,dtype=np.float32)
        for i,word in enumerate(words):
            h1=int(hashlib.md5(word.encode()).hexdigest(),16);w=1.0/(np.log(i+2))
            vec[h1%self.d]+=w
            h2=int(hashlib.sha256(word.encode()).hexdigest(),16);vec[h2%self.d]+=w*0.5
            if i<len(words)-1:
                bg=word+"_"+words[i+1]
                h3=int(hashlib.md5(bg.encode()).hexdigest(),16);vec[h3%self.d]+=w*0.3
        norm=np.linalg.norm(vec)
        if norm>1e-8: vec/=norm
        return vec
    def _snorm(self,M):
        U,S,Vt=np.linalg.svd(M,full_matrices=False)
        return (U@np.diag(np.clip(S,0.0,1.0))@Vt).astype(np.float32)
    def _write_scar(self,x,u_before,u_after,delta_u,text,temp):
        alpha=0.08
        U,S,Vt=np.linalg.svd(np.outer(x,x[:self.r]),full_matrices=False)
        u_vec=U[:,0] if U.shape[1]>0 else x
        v_vec=Vt[0,:self.r] if Vt.shape[0]>0 else np.ones(self.r)/np.sqrt(self.r)
        su=alpha*np.outer(u_vec,v_vec)
        if su.shape==self.C.shape: self.C=self._snorm(self.C+su)
        scar={"t":self.t,"ts":time.time(),"text":text[:200],
              "u_before":round(u_before,4),"u_after":round(u_after,4),
              "delta_u":round(delta_u,4),"temp":round(temp,1)}
        self.scars.append(scar)
        try:
            with open(self.scar_path,"a") as f: f.write(json.dumps(scar)+"\n")
        except: pass
        print(f"  ✨ INSIGHT #{self.n_insights}: {u_before:.1%} → {u_after:.1%}")
    def _save(self):
        try:
            np.savez_compressed(self.state_path,C=self.C,v=self.v,
                t=np.array([self.t]),n_thoughts=np.array([self.n_thoughts]),
                n_insights=np.array([self.n_insights]),n_blocked=np.array([self.n_blocked]),
                sigma=np.array([self.sigma]))
        except Exception as e: print(f"Save failed: {e}")
    def _load(self):
        if not self.state_path.exists(): return
        try:
            d=np.load(self.state_path,allow_pickle=True)
            self.C=d["C"];self.v=d["v"];self.t=int(d["t"][0])
            self.n_thoughts=int(d["n_thoughts"][0]);self.n_insights=int(d["n_insights"][0])
            self.n_blocked=int(d["n_blocked"][0]);self.sigma=float(d["sigma"][0])
        except Exception as e: print(f"Load failed ({e}) — fresh start")
