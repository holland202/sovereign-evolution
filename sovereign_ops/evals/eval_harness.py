#!/usr/bin/env python3
"""
SOVEREIGN OPS - eval_harness.py
================================
A regression suite, not a demo. Every eval here is something that was
ACTUALLY verified false-or-true earlier, not a placeholder.

Rule adopted from meta_prompt.txt: capability evals + regression evals,
tracked with pass/fail, not vibes. Run this before trusting any change
to causal_inference.py, conformal_prediction.py, or the SHO pipeline.

Add new evals as functions named eval_*(). Each returns (passed: bool, detail: str).
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def eval_dsep_confounder():
    """Classic confounder: Z->T, Z->Y, T->Y. Valid backdoor set must be {Z}."""
    from fixed_causal import CausalDAG, find_valid_backdoor_set
    dag = CausalDAG()
    for n in ['Z', 'T', 'Y']:
        dag.add_node(n)
    dag.add_edge('Z', 'T')
    dag.add_edge('Z', 'Y')
    dag.add_edge('T', 'Y')
    result = find_valid_backdoor_set(dag, 'T', 'Y')
    passed = result == {'Z'}
    return passed, f"got {result}, expected {{'Z'}}"


def eval_dsep_no_confounding():
    """T->Y only. Valid backdoor set must be empty."""
    from fixed_causal import CausalDAG, find_valid_backdoor_set
    dag = CausalDAG()
    for n in ['T', 'Y', 'W']:
        dag.add_node(n)
    dag.add_edge('T', 'Y')
    result = find_valid_backdoor_set(dag, 'T', 'Y')
    passed = result == set()
    return passed, f"got {result}, expected set()"


def eval_dsep_collider_trap():
    """T->C<-Y. Conditioning on collider C must OPEN the path, not close it.
    This is the case naive implementations get backwards."""
    from fixed_causal import CausalDAG
    dag = CausalDAG()
    for n in ['T', 'Y', 'C']:
        dag.add_node(n)
    dag.add_edge('T', 'C')
    dag.add_edge('Y', 'C')
    dsep_empty = dag.d_separated('T', 'Y', set())
    dsep_given_c = dag.d_separated('T', 'Y', {'C'})
    passed = (dsep_empty is True) and (dsep_given_c is False)
    return passed, f"d-sep(empty)={dsep_empty} (want True), d-sep({{C}})={dsep_given_c} (want False)"


def eval_conformal_coverage_gaussian():
    """Fixed conformal predictor must average >= 89% empirical coverage for a
    90% target across 20 independent trials. Single-trial coverage has real
    sampling variance at n=500 (a single draw of 0.864 is not a bug, it's
    noise) -- averaging is the statistically correct check, not a loosened
    threshold to force a pass."""
    from fixed_conformal import FixedConformalPredictor
    n_cal, n_test, n_trials = 500, 2000, 20
    coverages = []
    for trial in range(n_trials):
        rng = np.random.RandomState(trial)
        true_cal = rng.randn(n_cal) * 5
        pred_cal = true_cal + rng.randn(n_cal) * 2.0
        cp = FixedConformalPredictor(confidence=0.9)
        cp.calibrate(true_cal, pred_cal)
        true_test = rng.randn(n_test) * 5
        pred_test = true_test + rng.randn(n_test) * 2.0
        covered = sum(1 for t, p in zip(true_test, pred_test)
                      if cp.predict_interval(p)[0] <= t <= cp.predict_interval(p)[1])
        coverages.append(covered / n_test)
    mean_coverage = float(np.mean(coverages))
    passed = mean_coverage >= 0.89
    return passed, f"mean coverage over {n_trials} trials={mean_coverage:.4f} (range {min(coverages):.3f}-{max(coverages):.3f}), target>=0.89"


def eval_conformal_not_self_referential():
    """Regression guard: calibration must actually depend on prediction error.
    If someone reintroduces the response-vs-itself bug, this catches it:
    a model with LARGE error must produce a WIDER interval than a model
    with small error, calibrated on the same true values."""
    from fixed_conformal import FixedConformalPredictor
    np.random.seed(2)
    true_vals = np.random.randn(300) * 5

    good_model_pred = true_vals + np.random.randn(300) * 0.5   # low error
    bad_model_pred = true_vals + np.random.randn(300) * 5.0    # high error

    cp_good = FixedConformalPredictor(confidence=0.9)
    cp_good.calibrate(true_vals, good_model_pred)
    cp_bad = FixedConformalPredictor(confidence=0.9)
    cp_bad.calibrate(true_vals, bad_model_pred)

    lo_g, hi_g = cp_good.predict_interval(0.0)
    lo_b, hi_b = cp_bad.predict_interval(0.0)
    width_good = hi_g - lo_g
    width_bad = hi_b - lo_b
    passed = width_bad > width_good
    return passed, f"good_model_width={width_good:.3f}, bad_model_width={width_bad:.3f} (bad must be wider)"


def run_all():
    evals = [v for k, v in sorted(globals().items()) if k.startswith("eval_")]
    results = []
    for fn in evals:
        try:
            passed, detail = fn()
        except Exception as e:
            passed, detail = False, f"EXCEPTION: {e}"
        results.append((fn.__name__, passed, detail))

    print(f"\n{'='*70}\nSOVEREIGN OPS EVAL RUN\n{'='*70}")
    n_pass = sum(1 for _, p, _ in results if p)
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}\n       {detail}")
    print(f"{'='*70}\n{n_pass}/{len(results)} passed\n{'='*70}\n")
    return n_pass == len(results)


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
