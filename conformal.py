#!/usr/bin/env python3
"""
conformal.py — split conformal prediction, and a test that can fail.

Ported from fixed_conformal.py (Drive, 2026-07-02, 2841 bytes, two identical
copies).

CARRIED FROM THE SOURCE
-----------------------
FIX-1  nonconformity compares a MODEL'S output against the TRUE label, never
       a label against itself. Self-comparison yields all-zero scores, a
       zero-width interval, and a coverage figure that measures nothing.
       That is the real fix and it is preserved exactly.

NEW IN THIS PORT
----------------
FIX-2  the tests assert. The source's __main__ printed two coverage figures;
       the first computed a boolean and printed it, the second printed
       "(should still be >= 90%)" and never checked. Nothing could fail.

FIX-3  ANTI-VACUITY CONTROL. The source demonstrated coverage at 90% and
       never demonstrated that UNDER-coverage would be detected. A coverage
       test that has only ever seen adequate coverage is the same defect
       class as a gate that has only ever refused. P3 below calibrates on
       low-noise data and tests on high-noise data; coverage MUST fall well
       below target, or the instrument cannot detect the failure it exists
       to detect.

FIX-4  the 0.02 slack is justified rather than asserted. At n_test = 2000
       and p = 0.9 the standard error of the coverage estimate is
       sqrt(0.9 * 0.1 / 2000) = 0.0067, so 0.02 is approximately three
       standard errors. Stated, and computed in the output rather than
       hardcoded as folklore.

FIX-5  predict_interval sorts once at calibration instead of on every call.
       The source re-sorted 500 scores twice per test item in the second
       experiment -- 8000 sorts. Not a correctness bug; it made the second
       loop inconsistent with the first.

FIX-6  empty calibration raises instead of IndexError.

NOT ADDRESSED
-------------
Split conformal assumes exchangeability between calibration and test data.
Every experiment here draws both from the same process, so exchangeability
holds by construction and is never tested. Under covariate shift the
guarantee does not hold without modification. See P4.

Requires NumPy (as the source did, so the figures remain comparable).

    python3 conformal.py
    python3 conformal.py --sabotage    # restores self-comparison; must exit 1

REGISTERED BEFORE RUNNING
-------------------------
QUAL-1  Calibration scores are non-degenerate -- nonzero spread. If they are
        all zero the predictor is self-comparing and nothing below means
        anything.
P1      Gaussian noise: empirical coverage >= 0.90 - 3*SE.
P2      Exponential (skewed, non-Gaussian) noise: same bound. This is the
        distribution-free property.
P3      ANTI-VACUITY. Calibrated on sigma=0.5, tested on sigma=4.0:
        coverage MUST fall below 0.75. If it does not, this test cannot
        detect under-coverage and P1/P2 carry no information.
P4      UNRUN. Coverage under covariate shift, where calibration and test
        distributions differ in their inputs rather than their noise. Split
        conformal is not guaranteed there. No number here bears on it.
"""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np

__all__ = ["nonconformity_score", "ConformalPredictor"]

SEED = 0
N_CAL, N_TEST = 500, 2000
CONFIDENCE = 0.90


def nonconformity_score(true_val, pred_val, self_compare: bool = False):
    """FIX-1: |true - predicted|. With self_compare (sabotage only) this
    becomes |true - true| = 0, which is the bug the source fixed."""
    if self_compare:
        return abs(true_val - true_val)
    return abs(true_val - pred_val)


class ConformalPredictor:
    def __init__(self, confidence: float = CONFIDENCE, self_compare: bool = False):
        if not 0.0 < confidence < 1.0:
            raise ValueError("confidence must be in (0, 1)")
        self.confidence = confidence
        self.alpha = 1.0 - confidence
        self._sorted: list[float] = []
        self._self_compare = self_compare

    def calibrate(self, true_vals, model_preds) -> "ConformalPredictor":
        """Calibrate on held-out (true, predicted) pairs."""
        scores = [nonconformity_score(t, p, self._self_compare)
                  for t, p in zip(true_vals, model_preds)]
        if not scores:
            raise ValueError("calibration set is empty")  # FIX-6
        self._sorted = sorted(scores)                      # FIX-5: sort once
        return self

    @property
    def scores(self) -> list[float]:
        return list(self._sorted)

    def quantile(self) -> float:
        n = len(self._sorted)
        if n == 0:
            raise RuntimeError("calibrate() before predict_interval()")
        idx = min(int(math.ceil((n + 1) * (1 - self.alpha))), n)
        return self._sorted[idx - 1]

    def predict_interval(self, point_pred):
        q = self.quantile()
        return point_pred - q, point_pred + q


def coverage(cp: ConformalPredictor, true_vals, preds) -> float:
    q = cp.quantile()                                      # FIX-5: once
    hits = sum(1 for t, p in zip(true_vals, preds) if abs(t - p) <= q)
    return hits / len(true_vals)


def se(p: float, n: int) -> float:
    return math.sqrt(p * (1 - p) / n)


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sabotage", action="store_true",
                    help="restore self-comparison; the suite MUST fail")
    args = ap.parse_args()

    rng = np.random.RandomState(SEED)
    tol = 3 * se(CONFIDENCE, N_TEST)

    print("=" * 70)
    print("SPLIT CONFORMAL PREDICTION")
    print("=" * 70)
    print(f"seed {SEED}   n_cal {N_CAL}   n_test {N_TEST}   target {CONFIDENCE:.0%}")
    print(f"numpy {np.__version__}   python {sys.version.split()[0]}  {sys.platform}")
    print(f"tolerance 3*SE = 3*sqrt({CONFIDENCE}*{1-CONFIDENCE:.1f}/{N_TEST}) "
          f"= {tol:.4f}   (FIX-4: the source's 0.02, justified)")
    print(f"sabotage {args.sabotage}")
    print()

    sc = args.sabotage

    # -- QUAL-1 ---------------------------------------------------------
    print("-- QUAL-1  calibration scores are non-degenerate " + "-" * 20)
    t_cal = rng.randn(N_CAL) * 5
    p_cal = t_cal + rng.randn(N_CAL) * 2.0
    cp = ConformalPredictor(CONFIDENCE, self_compare=sc).calibrate(t_cal, p_cal)
    spread = max(cp.scores) - min(cp.scores)
    q1 = check("nonconformity scores vary", spread > 1e-9,
               f"spread {spread:.4f}, quantile {cp.quantile():.4f}")
    if not q1:
        print("\n  Scores are all zero: the predictor is self-comparing.")
        print("  Every interval has zero width. Nothing below is meaningful.")

    # -- P1 -------------------------------------------------------------
    print("\n-- P1  Gaussian noise " + "-" * 46)
    t_test = rng.randn(N_TEST) * 5
    p_test = t_test + rng.randn(N_TEST) * 2.0
    cov1 = coverage(cp, t_test, p_test)
    check(f"coverage >= {CONFIDENCE - tol:.4f}", cov1 >= CONFIDENCE - tol,
          f"{cov1:.1%}")

    # -- P2 -------------------------------------------------------------
    print("\n-- P2  exponential noise — the distribution-free property " + "-" * 10)
    t_cal2 = rng.randn(N_CAL) * 5
    p_cal2 = t_cal2 + rng.exponential(2.0, N_CAL) - 2.0
    cp2 = ConformalPredictor(CONFIDENCE, self_compare=sc).calibrate(t_cal2, p_cal2)
    t_test2 = rng.randn(N_TEST) * 5
    p_test2 = t_test2 + rng.exponential(2.0, N_TEST) - 2.0
    cov2 = coverage(cp2, t_test2, p_test2)
    check(f"coverage >= {CONFIDENCE - tol:.4f} under skewed noise",
          cov2 >= CONFIDENCE - tol, f"{cov2:.1%}")

    # -- P3 -------------------------------------------------------------
    print("\n-- P3  ANTI-VACUITY: under-coverage must be detectable " + "-" * 13)
    print("  calibrate on sigma=0.5, test on sigma=4.0 — the interval is")
    print("  far too narrow and coverage MUST collapse.")
    t_c3 = rng.randn(N_CAL) * 5
    p_c3 = t_c3 + rng.randn(N_CAL) * 0.5
    cp3 = ConformalPredictor(CONFIDENCE, self_compare=sc).calibrate(t_c3, p_c3)
    t_t3 = rng.randn(N_TEST) * 5
    p_t3 = t_t3 + rng.randn(N_TEST) * 4.0
    cov3 = coverage(cp3, t_t3, p_t3)
    p3 = check("miscalibrated predictor UNDER-covers (< 0.75)", cov3 < 0.75,
               f"{cov3:.1%}")
    if not p3:
        print("\n  This test cannot detect under-coverage. P1 and P2 above")
        print("  therefore carry no information about the guarantee.")

    # -- P4 -------------------------------------------------------------
    print("\n-- P4  REGISTERED, NOT RUN " + "-" * 42)
    print("  Coverage under covariate shift, where calibration and test")
    print("  INPUTS differ rather than their noise. Split conformal assumes")
    print("  exchangeability; every experiment above draws both sides from")
    print("  the same process, so exchangeability holds by construction and")
    print("  is never tested. STATUS: NOT VALIDATED.")

    failed = [n for n, ok in RESULTS if not ok]
    print("\n" + "=" * 70)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    print(f"  gaussian {cov1:.1%}   exponential {cov2:.1%}   "
          f"miscalibrated {cov3:.1%}")
    if args.sabotage:
        if failed:
            print("SABOTAGE detected: " + ", ".join(failed[:3]))
            print("Self-comparison collapses the intervals. The suite can fail.")
            return 1
        print("SABOTAGE NOT DETECTED — this suite is vacuous.")
        return 2
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All assertions passed.")
    print("Scope: synthetic data, exchangeable by construction, one seed.")
    print("This does not establish coverage on real data or under shift.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
