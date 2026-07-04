"""
IGAR DEMO: full loop, one simulated thermal cycle.
Shows the integrity-gated governor driving real compute decisions and
reporting honestly when it can't meet its own bar.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from igar_core import ThermalIntegrityGate, ThrottledConformalPredictor, integrity
from fixed_causal import CausalDAG, find_valid_backdoor_set

np.random.seed(3)
gate = ThermalIntegrityGate()

# A DAG needing 2 variables for a valid explanation (SENTINEL-style: two
# independent confounders on a sensor pair)
dag = CausalDAG()
for n in ['ambient_temp', 'line_pressure', 'valve_state', 'anomaly_flag']:
    dag.add_node(n)
dag.add_edge('ambient_temp', 'valve_state')
dag.add_edge('line_pressure', 'valve_state')
dag.add_edge('ambient_temp', 'anomaly_flag')
dag.add_edge('line_pressure', 'anomaly_flag')

true_cal = np.random.randn(400) * 5
pred_cal = true_cal + np.random.randn(400) * 2.0

print("Simulating a thermal cycle: cool -> throttle -> scar_lock -> cool\n")
temps = [33, 36, 39, 43, 39, 35, 32]
for temp in temps:
    decision = gate.compute_budget(temp_c=temp, beta=1.5)
    backdoor = find_valid_backdoor_set(dag, 'valve_state', 'anomaly_flag',
                                         max_size=decision["causal_max_size"])
    cp = ThrottledConformalPredictor(confidence=0.9)
    cp.calibrate(true_cal, pred_cal, fraction=decision["calibration_fraction"])
    lo, hi = cp.interval(0.0)
    width = hi - lo

    explanation = backdoor if backdoor is not None else "INSUFFICIENT BUDGET -- escalate, do not guess"
    print(f"temp={temp:>4.1f}C  level={decision['level']:10s}  I={decision['I']:.3f}  "
          f"causal_max_size={decision['causal_max_size']}  interval_width={width:.2f}")
    print(f"          -> causal explanation: {explanation}")
print("\nNote: causal search NARROWS as temp rises (max_size drops 3->2->1).")
print("Interval width is NOT guaranteed to widen under throttling -- less")
print("calibration data gives a NOISIER estimate of the same quantile, not")
print("a systematically wider one (verified: widths above went 6.47/6.47/")
print("6.39/6.07, i.e. slightly narrower here, by chance). The property that")
print("actually holds, proven in test1, is AGGREGATE coverage across many")
print("decisions -- not that any single throttled interval is wider.")
print("At max_size=1 it correctly admits it cannot find the true 2-variable")
print("explanation rather than guessing one variable and calling it done --")
print("that property IS guaranteed, structurally, every time.")
