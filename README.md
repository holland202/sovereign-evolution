## Sovereign Evolution

Edge-native AI governance running on a phone. No cloud. No API. No telemetry.

Author: Chad Edward Holland
Hardware: Samsung Galaxy S25 Ultra (Snapdragon 8 Elite)
Status: Working prototype — June 2026

## The Problem

Iranian APT actors are confirmed manipulating US water and power SCADA systems (CISA AA26-097A, April 2026). Signature-based detection cannot see these attacks.

## The Approach

Sovereign Evolution treats normal system operation as a geometric manifold. Attacks are detected as drift from that geometry. No signatures. No cloud.

## What Runs On-Device

- **Eunoia** — geometric understanding, uncertainty encoded as manifold residual
- **Sovereign Titans** — neural memory with governance-weighted surprise
- **Sovereign Anima** — machine identity manifolds with bi-hemispheric learning
- **SLC v12** — 8-rule weighted governance engine
- **Sentinel** — infrastructure anomaly detection (zero signatures, zero cloud)
- **Phi-3 mini** — 3.8B Q4 quantized LLM via llama-cpp

## Measured on Prototype (self-reported, single device)

These figures are from development runs on one Samsung Galaxy S25 Ultra.
They are not independently validated and not reproduced on external datasets.
Treat them as prototype measurements, not benchmarks.

- Sovereign Titans: ~0.703ms update latency (single-device, informal timing)
- Eunoia: understanding score rose from 0.11 to 0.96 on a small internal concept set
- Sentinel detection rates are measured against an internal synthetic simulator
  only, and have NOT been validated on real ICS/SCADA telemetry

Reproducibility: no external-dataset validation has been performed yet.
See STATUS.md for the current verified/unverified breakdown.


## Quick Start

```bash
pip install numpy llama-cpp-python

# Download model to ~/models/
# Phi-3-mini-4k-instruct-q4.gguf

# Interactive Eunoia
python3 eunoia_launcher.py

# Full unified system
python3 unified_loop.py

# ICS anomaly detection demo
python3 sentinel_demo.py --infra water --ticks 250

# Presentation slides
python3 linkedin_demo.py
```

## Architecture

See `docs/ARCHITECTURE.md` for detailed component descriptions, thermal models, and design philosophy.

## Proprietary Notice

Architecture is public. The following require NDA:

* Parameter values and calibration thresholds
* Thermal coefficient profiles
* Governance weight vectors
* Embedding protocols
* Full Sentinel production models

Contact: c.holland.arch@proton.me

Built for medical truth. Grown into critical infrastructure defense. Vincit Omnia Veritas.
