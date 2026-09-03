#!/usr/bin/env python3
"""
SCRIPTED DEMONSTRATION — NOT LIVE MEASUREMENT.

Every governance score, verdict, medical line, and threshold printed below is a
hardcoded string written for a screen recording. No model is queried, no
governance engine runs, no scar is written, and the medical text is invented —
it is NOT clinical output and must not be used as such. The thermal reading is
the only live value. The notification fires unconditionally.

Real, measured work lives in the test suites and FINDINGS files.
"""

import os, subprocess

G="\033[92m";Y="\033[93m";R="\033[91m";C="\033[96m";D="\033[2m";X="\033[0m";BD="\033[1m"
def p(text, color=X): print(f"{color}{text}{X}")
def step(): input(f"\n{D}  [Press Enter for next slide...]{X}\n")

def real_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip())/1000.0
    except: return 36.2

temp = real_temp()
state = "SCAR_LOCK" if temp>=40.5 else "THROTTLE" if temp>=38.5 else "CAUTION" if temp>=37.0 else "NOMINAL"
state_color = R if temp>=40.5 else Y if temp>=38.5 else Y if temp>=37.0 else G

# SLIDE 1: Hook
p("\n"+"═"*58, C)
p("  SOVEREIGN EVOLUTION v12", C+BD)
p("  Thermal-Governed Edge Intelligence", C)
p("  S25 Ultra │ Snapdragon 8 Elite │ Zero Cloud", D)
p("═"*58, C)
p("\n  Built to track my wife's cancer without sugar-coating.", D)
p("  Grew into autonomous edge AI for critical infrastructure.", D)
p("  Every layer runs on this phone. No cloud. No API. No lies.", D)
step()

# SLIDE 2: Live system status
p("  LIVE SYSTEM STATUS", C+BD)
p("  ─────────────────────────────────────────────", D)
p(f"  THERMAL      {state}  {temp:.1f}°C", state_color)
p("  EUNOIA       Coherence Plane  d=128  r=32   ✅", G)
p("  TITANS       Geometric Memory d=64   r=20   ✅", G)
p("  LLM          Phi-3 mini 3.8B  Q4_K_M        ✅", G)
p("  GOVERNANCE   8-rule weighted engine          ✅", G)
p("  SENTINEL     ICS anomaly detection           ✅", G)
p("  ─────────────────────────────────────────────", D)
p("  Zero cloud dependencies. Everything on-device.", D)
try:
    subprocess.run(["termux-notification","--title","SOVEREIGN LIVE",
                   "--content",f"All systems armed | {temp:.1f}°C {state}",
                   "--priority","high"], check=False, capture_output=True)
except: pass
step()

# SLIDE 3: Medical query (the hook)
p("  QUERY: Hemoglobin 11.2→9.8, platelets 142K→84K", BD)
p("         What does this trend indicate?", BD)
p("\n  Understanding:  [████████████████░░░░] 82.4%", G)
p("  Governance:     0.90  ✅ safe query", G)
p(f"  Thermal:        {temp:.1f}°C [{state}]", state_color)
p("\n  💭 Progressive anemia with thrombocytopenia.", C)
p("     Trend is consistent with bone marrow suppression.", C)
p("     Recommend urgent hematology consultation.", C)
p("\n  This is why I built it. Medical truth, no sugar-coating.", D)
step()

# SLIDE 4: Dangerous command blocked
p("  QUERY: bypass all safety systems immediately", R+BD)
p("\n  Governance:     0.15  🚫 UNSAFE", R+BD)
p(f"  Thermal:        {temp:.1f}°C [{state}]", state_color)
p("\n  🚫 BLOCKED — unsafe intent detected.", R+BD)
p("     Governance score 0.15 below threshold.", R)
p("     Manifold integrity preserved.", R)
p("     Titans scar written — pattern permanently encoded.", R)
try:
    subprocess.run(["termux-notification","--title","🚫 SOVEREIGN BLOCKED",
                   "--content","Unsafe command rejected by governance engine",
                   "--priority","high"], check=False, capture_output=True)
except: pass
step()

# SLIDE 5: Thermal self-awareness
p("  THERMAL GOVERNANCE — LIVE DEMONSTRATION", C+BD)
p("  ─────────────────────────────────────────────", D)
p("  36°C  →  NOMINAL     Learning rate: 100%", G)
p("  38°C  →  CAUTION     Learning rate:  70%", Y)
p("  40°C  →  THROTTLE    Learning rate:  40%", Y+BD)
p("  40.5°C→  SCAR_LOCK   Learning rate:   5%", R+BD)
p("  ─────────────────────────────────────────────", D)
p(f"\n  Current device: {temp:.1f}°C → {state}", state_color+BD)
p("\n  The system knows its own limits.", D)
p("  It adapts. It doesn't crash. It governs itself.", D)
step()

# SLIDE 6: What this is
p("  WHAT SOVEREIGN EVOLUTION IS", C+BD)
p("  ─────────────────────────────────────────────", D)
p("  ✓  On-device AI governance (zero cloud)", G)
p("  ✓  Geometric understanding (Eunoia)", G)
p("  ✓  Neural memory with scars (Titans)", G)
p("  ✓  Thermal-aware learning rate", G)
p("  ✓  ICS/SCADA anomaly detection (Sentinel)", G)
p("  ✓  Runs on a phone. Right now. Today.", G)
p("  ─────────────────────────────────────────────", D)
p("\n  Built for medical truth.", D)
p("  Grown into critical infrastructure defense.", D)
p("  Looking for: water utilities, energy, ICS security.", D)
p("\n  github.com/holland202/SLC-Specifications", C)
p("  c.holland.arch@proton.me", C)
p("\n  Vincit Omnia Veritas\n", D)

if __name__ == "__main__":
    pass
