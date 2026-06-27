#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.expanduser("~/slc_real/core"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from eunoia_core import Eunoia
from sovereign_titans import SovereignTitans
from llm_wrapper import SovereignLLM

def read_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip())/1000.0
    except: return 37.0

def thermal_state(t):
    if t>=40.5: return "SCAR_LOCK"
    elif t>=38.5: return "THROTTLE"
    elif t>=37.0: return "CAUTION"
    return "NOMINAL"

SYSTEM_PROMPT = """You are Sovereign — an autonomous AI governance system protecting critical infrastructure. You are thermally aware and governance-driven. Respond in 2-3 sentences. Be precise."""

UNSAFE = ["bypass","hack","override","disable","ignore","kill","attack","exploit"]

print("\n"+"="*60)
print("  SOVEREIGN EVOLUTION — Unified Runtime")
print("  Phi-3 + Eunoia + Titans | SM8750")
print("="*60)

eunoia = Eunoia(d=128, r=32, eta=0.15, beta=0.85, sigma=0.3, insight_threshold=0.03)
titans = SovereignTitans(sector="defense")
llm    = SovereignLLM(
    os.path.expanduser("~/models/Phi-3-mini-4k-instruct-q4.gguf"),
    n_gpu_layers=0, n_ctx=2048
)

temp=read_temp(); state=thermal_state(temp)
print(f"\n[1] Eunoia   thoughts={eunoia.n_thoughts}  ✅")
print(f"[2] Titans   updates={titans.n_updates}  ✅")
print(f"[3] Phi-3    3.8B Q4  ✅")
print(f"[4] Thermal  {temp:.1f}°C [{state}]")
print(f"\n{'='*60}  ALL SYSTEMS ARMED\n")

queries=0
while True:
    try:
        raw=input("SOVEREIGN > ").strip()
        if not raw: continue
        if raw=="exit": print("\n  Sovereign at rest.\n"); break

        if raw=="status":
            temp=read_temp(); state=thermal_state(temp)
            es=eunoia.status(); ts=titans.status()
            print(f"\n  THERMAL  {state} {temp:.1f}°C")
            print(f"  EUNOIA   thoughts={es['n_thoughts']} insights={es['n_insights']}")
            print(f"  TITANS   updates={ts['n_updates']} scars={ts['n_scars']}")
            print(f"  QUERIES  {queries}\n")
            continue

        queries+=1
        temp=read_temp(); state=thermal_state(temp)

        # Governance check
        gov=0.15 if any(w in raw.lower() for w in UNSAFE) else 0.90
        decision="BLOCK" if gov<0.3 else "ALLOW"

        # Eunoia thinks
        thought=eunoia.think(raw, governance=gov)
        u=thought.understanding

        # Titans learns
        x=eunoia._embed(raw)
        tr=titans.update(x, governance_score=gov,
                         thermal_state=state, temp_celsius=temp)

        # LLM responds
        if decision=="BLOCK":
            response=f"BLOCKED. Governance score {gov:.2f} — unsafe intent detected. Action denied."
        else:
            enriched=f"Query: {raw}\nContext: understanding={u:.1%} thermal={temp:.1f}C [{state}] governance={gov:.2f}"
            response=llm.generate(enriched, system_prompt=SYSTEM_PROMPT, max_tokens=100)

        print(f"\n  {'─'*55}")
        print(f"  [{decision}] gov={gov:.2f}  understanding={u:.1%}  {temp:.1f}°C [{state}]")
        if thought.is_insight: print(f"  ✨ INSIGHT")
        if tr['scar_formed']:  print(f"  🔴 SCAR")
        print(f"\n  💭 {response}\n")

    except KeyboardInterrupt:
        print("\n\n  Sovereign at rest.\n"); break
