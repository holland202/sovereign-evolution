"""
IGAR: Integrity-Gated Adaptive Rigor
======================================
Binds a device integrity signal to real-time compute throttling of a
verified causal/conformal governance stack.

PUBLIC VERSION NOTICE:
The thermal thresholds and integrity-formula weights below are
ILLUSTRATIVE PLACEHOLDERS, not production calibration values. Per this
repo's Proprietary Notice, parameter values, calibration thresholds, and
governance weight vectors are NDA-gated and withheld here. The mechanism
and math shown are real and tested; the constants are not the production
ones. Contact c.holland.arch@proton.me for licensed access to calibrated
values.

THE CLAIM (testable, proven -- see tests in this same directory):
  Throttling compute based on an integrity signal I(t) does NOT break the
  conformal coverage guarantee, PROVIDED the throttle decision depends
  only on device state (thermal telemetry) and never on the current test
  point's true label. This is a direct consequence of conformal
  prediction's exchangeability requirement: calibration validity depends
  on how scores are computed, not on how much compute was spent computing
  them, as long as the compute-level decision is independent of the test
  label being scored.

  Verified (15-trial average): mean coverage with throttling active =
  89.3% (range 87.0-91.4%) vs 89.7% for a non-throttled baseline --
  statistically indistinguishable. See test1_coverage_survives_throttle.py.

  Also verified: when the compute budget is genuinely insufficient to
  find a valid causal explanation, the system returns None (escalate)
  rather than silently guessing a wrong one. See test2_honest_failure.py.

NOVELTY NOTE: before building this, 4 adjacent research directions were
checked (thermal/budget-aware conformal prediction on edge devices,
budget-constrained causal adjustment set selection, Hamiltonian/symplectic
conservation-violation anomaly detection, Wasserstein-attention sensor
fusion) -- all four already exist in published work from 2022-2026. The
general pattern here (throttle compute under a resource constraint, keep
the statistical guarantee) is known, active research, not a new idea.
What's specific to this repo is the integration and the device it runs on.
"""
import sys
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixed_causal import CausalDAG, find_valid_backdoor_set

# --- ILLUSTRATIVE PLACEHOLDER VALUES (see notice above) ---
COLD_FLOOR = 30.0
THROTTLE = 37.0
SCAR_LOCK = 42.0


def integrity(Hm, Cs, Ct, beta):
    """Illustrative governance formula SHAPE. Production weights are
    proprietary and NDA-gated; the equal-weighted placeholder below
    preserves the formula's structure for demonstration only."""
    return 0.25 * Hm + 0.25 * Cs + 0.25 * Ct - 0.25 * min(1, beta / 7)


class ThermalIntegrityGate:
    """
    Maps live thermal state -> a compute budget level, using ONLY device
    telemetry. Never sees the test label. This is the structural guarantee
    that keeps conformal validity intact -- enforced by the function
    signature itself, not just by convention.
    """
    def __init__(self):
        self.history = []

    def compute_budget(self, temp_c: float, beta: float, Hm: float = 0.9, Cs: float = 0.9):
        """
        Returns (level, hamiltonian_steps, causal_max_size, calibration_fraction).
        Driven ENTIRELY by (temp_c, beta, Hm, Cs) -- device/system state.
        No parameter here is, or could be, the ground-truth anomaly label.
        """
        Ct = 1.0 - min(1.0, max(0.0, (temp_c - COLD_FLOOR) / (SCAR_LOCK - COLD_FLOOR)))
        I = integrity(Hm, Cs, Ct, beta)

        if temp_c >= SCAR_LOCK:
            level = "SCAR_LOCK"
            steps, max_size, cal_frac = 3, 1, 0.2
        elif temp_c >= THROTTLE:
            level = "THROTTLE"
            steps, max_size, cal_frac = 10, 2, 0.5
        else:
            level = "FULL"
            steps, max_size, cal_frac = 20, 3, 1.0

        record = {"temp_c": temp_c, "I": I, "level": level,
                   "hamiltonian_steps": steps, "causal_max_size": max_size,
                   "calibration_fraction": cal_frac}
        self.history.append(record)
        return record


class ThrottledConformalPredictor:
    """Calibration set size can be reduced by the gate (simulating 'less
    time to calibrate when thermally constrained'). Nonconformity function
    itself never changes -- only how much calibration data we had time
    to use."""
    def __init__(self, confidence=0.9):
        self.alpha = 1 - confidence
        self.scores = []

    def calibrate(self, true_vals, pred_vals, fraction=1.0):
        n_use = max(10, int(len(true_vals) * fraction))
        self.scores = [abs(t - p) for t, p in zip(true_vals[:n_use], pred_vals[:n_use])]

    def interval(self, point_pred):
        n = len(self.scores)
        q_idx = min(int(np.ceil((n + 1) * (1 - self.alpha))), n)
        threshold = sorted(self.scores)[q_idx - 1]
        return point_pred - threshold, point_pred + threshold
