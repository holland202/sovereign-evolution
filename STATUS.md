# STATUS — Verified vs. Unverified

This document states only what has been checked by running the code.
"Verified" means a test targeting the actual claim passes. Items marked
"in this repo" can be cloned and run by anyone, today.

Last updated: 2026-07-05.

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
- No third-party or multi-device validation has been performed.

---

## Honest summary
The verified core is a set of correct implementations of established
mathematics — low-rank manifold memory, Fisher-metric authentication,
Pearl causal inference, conformal prediction — each backed by a test.
Older docs sometimes overstate what these primitives do; this file is
the ground truth. When in doubt, run the test.

Vincit Omnia Veritas — but only when checked.
