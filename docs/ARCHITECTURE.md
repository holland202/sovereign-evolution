# Sovereign Evolution — Architecture

## Core Concepts

- **Manifold Learning**: Each component treats its domain as a geometric space where normal operation is a low-rank manifold. Anomalies appear as drift from that geometry.
- **Scars**: Permanent memory of anomalies encoded as rank-1 updates to the learned manifold. The geometry encodes history.
- **Thermal Governance**: Learning rate scales with device temperature (100% at nominal, 5% at SCAR_LOCK ≥40.5°C). The system self-throttles under heat.
- **No Cloud**: All processing on-device; no telemetry, no API calls, no external dependencies.

## Components

### Eunoia (Coherence Plane)
- 128-d hash-based semantic embedding (MD5 + SHA256 on words)
- **Manifold**: d=128, rank=32 low-rank matrix C
- **Understanding**: 1 - (residual_norm / input_norm); ranges [0, 1]
- **Insights**: Trigger when understanding jumps > 0.35 and previous understanding < 0.5
- State tracking: thoughts, insights, scars, blocked updates
- Stores state in `~/.sovereign_memory/eunoia_coherence.npz`

### Sovereign Titans (Governance-Gated Memory)
- 64-d manifold, rank-20
- **Scar Condition**: Surprise > theta_scar AND governance < theta_gov
- **Sector Thresholds**: Calibrated per infrastructure type
  - Defense: theta_scar=0.12, theta_gov=0.50
  - Healthcare: theta_scar=0.10, theta_gov=0.55
  - Aerospace: theta_scar=0.15, theta_gov=0.45
  - Robotics/Automotive: theta_scar=0.12, theta_gov=0.50
- Thermal-aware learning: eta_t = eta * phi(temp, state)
- Stores state in `~/.sovereign_memory/titans_{sector}.npz`

### Sovereign Anima (Machine Identity)
- Per-machine manifold (not class-level)
- **Bi-hemispheric learning**: HOT (live inference) and COOL (background learning during charging)
- Handoff when: charging AND temp < 37°C AND cool_updates ≥ 50 AND dt > 1 hour
- Geodesic distance guards against dangerous jumps (reject if > 0.15)
- Enables machine-specific anomaly detection

### Sentinel (Infrastructure Detection)
- **IGT Detector**: Jensen-Shannon divergence between rolling telemetry distribution and baseline
- **Profiles**: Power (voltage/freq/current), Water (flow/pressure/pH), Pipeline (pressure/flow/vibration), SCADA (generic PVs)
- **Threat Levels**: NOMINAL → WATCH → ELEVATED → SEVERE → CRITICAL
- **Audit Log**: Hash-chained append-only events for forensic compliance
- Supports attack injection: voltage surge, pH tampering, flow shutoff, comm floods, etc.

### LLM Wrapper (Phi-3 Mini Q4)
- 3.8B quantized model, runs without GPU layers
- Phi-3 chat format: `<|system|>` / `<|user|>` / `<|assistant|>` tokens
- max_tokens=100-120 per response, stops on `<|end|>` or `<|user|>`
- System prompt includes governance/thermal context

## Unified Loop

```
User Query
    ↓
Governance Check (unsafe keywords → score 0.15, else 0.90)
    ↓
Eunoia.think() — Geometric understanding
    ↓
Titans.update() — Memory consolidation + scar formation
    ↓
Decision: BLOCK if gov < 0.3, else invoke Phi-3
    ↓
Response (or BLOCKED message)
```

Each component respects thermal state and adjusts learning rates accordingly.

## Running

### Interactive Eunoia
```bash
python3 eunoia_launcher.py
# Commands: status, insights, bench <text>, compare <A> vs <B>, exit
```

### Full Unified System (requires Phi-3 model at ~/models/Phi-3-mini-4k-instruct-q4.gguf)
```bash
python3 unified_loop.py
# SOVEREIGN > [query]
```

### Sentinel Demo (ICS Anomaly Detection)
```bash
python3 sentinel_demo.py --infra water --ticks 250 --speed 0.08
python3 sentinel_demo.py --infra power
python3 sentinel_demo.py --infra pipeline
python3 sentinel_demo.py --infra scada
```

### LinkedIn Presentation
```bash
python3 linkedin_demo.py
```

## State & Persistence

- Eunoia state: `~/.sovereign_memory/eunoia_coherence.npz` (manifold C, momentum v, counters)
- Eunoia scars: `~/.sovereign_memory/eunoia_scars.jsonl` (insight history, one line per scar)
- Titans state: `~/.sovereign_memory/titans_{sector}.npz`
- Titans scars: `~/.sovereign_memory/titans_scars_{sector}.jsonl`
- Sentinel audit: `sentinel_{infra}_audit.jsonl` (hash-chained threat events)

## Thermal Model

Four states defined in each component:
- **NOMINAL** (≤37°C): full learning (phi=1.0)
- **CAUTION** (37-38.5°C): reduced learning (phi=0.7)
- **THROTTLE** (38.5-40.5°C): heavily reduced (phi=0.4)
- **SCAR_LOCK** (≥40.5°C): minimal updates (phi=0.05), prevents manifold collapse

## Design Philosophy

1. **Geometric Trust**: Normal operation defines a manifold. Attacks are geometric drift.
2. **On-Device Autonomy**: No cloud, no phone-home, no vendor lock-in.
3. **Thermal Awareness**: Hardware constraints are first-class, not afterthoughts.
4. **Persistent Memory**: Scars encode organizational learning in the manifold itself.
5. **Governance-First**: Every decision passes a safety check (governance score).

Built for medical truth. Grown into critical infrastructure defense.

**Vincit Omnia Veritas**

Contact: c.holland.arch@proton.me
