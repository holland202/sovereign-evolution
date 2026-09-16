# STATUS — Verified vs. Unverified

This document states only what has been checked by running the code.
"Verified" means a test targeting the actual claim passes. Items marked
"in this repo" can be cloned and run by anyone, today.

Claims in this file were verified on 2026-07-05. Ledger amended 2026-09-16 — see "Changes since this file was written" at the end. The verification date is deliberately not bumped: nothing below has been re-run since 2026-07-05, and moving the date without re-running would manufacture freshness this file exists to prevent.

---

## VERIFIED — in this repo, tests pass

### Eunoia (eunoia_core.py)
Understanding = 1 - ||residual||/||x||, the projection error onto a
learned coherence manifold. Verified by running: understanding of a
repeated phrase rises monotonically over training reps; an unseen phrase
stays near baseline (it reports low understanding for what it has not
learned).
- Honest scope: the high "understanding" figure is same-phrase absorption,
  NOT general concept comprehension. The learning rate (eta) sets how fast
  it rises; pin eta when quoting a number.

### Sovereign Titans (sovereign_titans.py)
Governance-gated manifold memory. Verified by running this file:
- Scar formation: high-surprise + low-governance inputs form scars.
- Governance gating: safe (high-governance) inputs form no scars.
- Recall: a burned-in pattern is recalled far above a random pattern.
- theta_scar = 0.12 is calibrated to the real surprise scale (~0.10-0.75).
  An earlier 2.0 value was unreachable; this repo ships 0.12.

### Causal backdoor engine (igar/fixed_causal.py)
From-scratch Pearl d-separation + backdoor criterion. Verified 6/6 on
hand-checked cases, including the collider traps: it refuses to adjust
for a collider, and correctly reports that conditioning on a collider
opens a path (Berkson's paradox). Deterministic across runs.

### Conformal prediction (sovereign_ops/fixed_conformal.py)
Distribution-free prediction intervals. Verified by running: empirical
coverage 89.5% against a 90% target, and 91.8% under non-Gaussian
(exponential) noise. Nonconformity compares model prediction against the
true label (never a label against itself).

### IGAR throttle tests (igar/test1_*.py, igar/test2_*.py)
- test1: conformal coverage survives thermal throttling (~88.8% aggregate).
- test2: under a constrained budget the causal engine returns "no valid
  explanation" (None) instead of fabricating a wrong adjustment set.
  Honest-failure behavior, verified.
- **AMENDED 2026-09-16.** When this entry was written on 2026-07-05, neither test carried a verdict gate — test2 had no `assert`, `raise` or `sys.exit` at all, so it could not fail. Gates were added in `367454e` (2026-08-14) and demonstrated in both directions; CI began gating on them in `c503bc9` (2026-08-23). The behaviour described above was real, but on 2026-07-05 "verified" rested on reading the output rather than on a check that could have returned otherwise.

---

## VERIFIED — public reference implementation pending

### SIC — Scarred Identity Chronicle
Low-rank manifold memory with thermally-gated scar updates. Verified 3/3
by running the private suite: irreversibility (the inverse event does NOT
undo a scar), path-dependence (U(A,B) != U(B,A)), rank preserved across
many scars. A public reference file (real algorithm, demo constants;
production calibration stays NDA per the Proprietary Notice) is being
prepared, and will ship with its reproduction test.

### VEST — manifold challenge-response authentication
Fisher-Riemannian challenge-response auth. Verified by running the
private suite: true-accept 300/300 for the exact manifold holder;
false-accept 0/300 for a near-miss manifold; Fisher distance rises
sharply with perturbation (a hard boundary, not a soft slope).
- Scope: validates the approximate-impostor threat model. It is NOT a
  proof against a cryptographic adversary solving for the manifold
  analytically. Public reference file ships with its test, as above.

---

## NOT VERIFIED — do not treat as established

- Sentinel detection rates come from an internal synthetic simulator and
  a BATADAL replay, NOT live ICS/SCADA telemetry. BATADAL results
  (7/7 attacks detected, precision ~0.31, recall ~0.73, calibrated on
  normal operation only) are in docs/BATADAL_VALIDATION.md — a public
  academic dataset, not a production deployment.
- Latency figures are informal single-device timings, not benchmarks.
- unified_loop.py governance is a keyword blocklist demo, not geometric
  reasoning.
- sovereign_anima.py is a concept/scaffold, not a validated component.
- linkedin_demo.py is a SCRIPTED WALKTHROUGH. Its printed scores and medical text are hardcoded, not measured (`8086d0e`, `1ebf7eb`, 2026-09-02).
- No third-party or multi-device validation has been performed.

---

## Honest summary
The verified core is a set of correct implementations of established
mathematics — low-rank manifold memory, Fisher-metric authentication,
Pearl causal inference, conformal prediction — each backed by a test.
Older docs sometimes overstate what these primitives do; this file is
the ground truth. When in doubt, run the test.

Vincit Omnia Veritas — but only when checked.


---

## Changes since this file was written

This file's claims were verified on 2026-07-05. The repository has moved
since. Nothing below has been re-verified; this section exists so the gap is
visible rather than silent.

| Commit | Date | Change | Bearing on this file |
|---|---|---|---|
| `367454e` | 2026-08-14 | igar: verdict gates added to both tests, demonstrated in both directions | Material. The IGAR entry above was written while test2 could not fail. |
| `f3f4b48` | 2026-08-15 | `sovereign_live.py` added | New component, not covered here. |
| `3fec937` | 2026-08-15 | license signing key fails loudly instead of failing open | Behaviour change, not covered here. |
| `884c58b` | 2026-08-15 | sector-threshold calibration values redacted from ARCHITECTURE.md | Values remain reachable in history prior to this commit. |
| `c503bc9` | 2026-08-23 | CI gates on the two igar tests | New verification surface. |
| `5efbac5` | 2026-08-23 | CI: install numpy — the first workflow run had failed at import | The workflow caught its own defect on first execution. |
| `49c5c6a` | 2026-09-02 | relicensed to MIT | — |
| `8086d0e`, `1ebf7eb` | 2026-09-02 | `linkedin_demo` relabelled: printed scores and medical text are hardcoded | Added to NOT VERIFIED above. |
| `8d3edbd` | 2026-09-16 | CITATION.cff, AUTHORS.md, PROVENANCE.md added | PROVENANCE.md cites this file as the evidence ledger. |

To close this gap properly, re-run the tests behind each VERIFIED entry on
device and record the output. Until that happens, treat every VERIFIED claim
above as carrying a 2026-07-05 date, not today's.
