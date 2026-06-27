#!/usr/bin/env python3
import sys,os,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from eunoia_core import Eunoia

def print_thought(t):
    u=t.understanding;filled=int(u*20);bar="█"*filled+"░"*(20-filled)
    print(f"\n{'─'*55}")
    if t.is_insight: print(f"  ✨ INSIGHT — geometry permanently changed")
    print(f"  Understanding:  [{bar}] {u:.1%}")
    print(f"  Coherence:      {t.coherence:.4f}")
    print(f"  State:          {'✅ Known' if t.is_known() else '❓ Uncertain' if t.is_uncertain() else '◐ Partial'}")
    print(f"  Temp:           {t.temp:.1f}°C [{t.thermal_state}]")
    print(f"\n  💭 {t.narrate()}\n")

# Calibrated parameters
e=Eunoia(d=128, r=32, eta=0.15, beta=0.85, sigma=0.3, insight_threshold=0.03)

print(f"\n{'='*55}")
print(f"  EUNOIA — THE COHERENCE PLANE")
print(f"  eta=0.15 | sigma=0.3 | insight_threshold=0.03")
print(f"  Commands: status, insights, bench <text>, compare <A> vs <B>, exit")
print(f"{'='*55}\n")

while True:
    try:
        raw=input("Eunoia > ").strip()
        if not raw: continue
        if raw=="exit": print("\n  ✨ Mind at rest.\n"); break

        elif raw=="status":
            s=e.status()
            print(f"\n{'─'*40}")
            for k,v in s.items(): print(f"  {k:<20} {v}")
            print()

        elif raw=="insights":
            recent=e.recent_insights(10)
            if not recent: print("\n  No insights yet.\n")
            else:
                print(f"\n  ✨ {len(e.scars)} total insights:")
                for sc in recent:
                    print(f"  t={sc['t']} | {sc['text'][:50]}")
                    print(f"    {sc['u_before']:.1%} → {sc['u_after']:.1%} (Δ={sc['delta_u']:.3f})")
                print()

        elif raw.startswith("bench "):
            # Run 50 repetitions of same text — shows learning curve
            text=raw[6:].strip()
            print(f"\n  📈 Learning curve — 50 repetitions of: '{text[:40]}'")
            print(f"  {'t':>4}  {'Understanding':>15}  {'Δ':>8}  {'Insight'}")
            prev_u=0.0
            for i in range(50):
                t=e.think(text,governance=0.9)
                delta=t.understanding-prev_u
                marker="✨ INSIGHT" if t.is_insight else ""
                if i%5==0 or t.is_insight:
                    bar="█"*int(t.understanding*20)+"░"*(20-int(t.understanding*20))
                    print(f"  {i+1:>4}  [{bar}] {t.understanding:.1%}  {delta:>+.3f}  {marker}")
                prev_u=t.understanding
            print(f"\n  Final understanding: {prev_u:.1%}")
            print(f"  Total insights: {e.n_insights}\n")

        elif raw.startswith("compare ") and " vs " in raw:
            parts=raw[8:].split(" vs ")
            r=e.compare(parts[0].strip(),parts[1].strip())
            print(f"\n  Relationship: {r['relationship']}")
            print(f"  Similarity:   {r['geometric_similarity']:.4f}\n")

        else:
            thought=e.think(raw,governance=0.9)
            print_thought(thought)

    except KeyboardInterrupt:
        print("\n\n  ✨ Mind at rest.\n"); break
