"""
TEST 2: When SCAR_LOCK throttles causal search to max_size=1, and the TRUE
minimal valid adjustment set requires 2 variables, does the system:
  (a) correctly report "no valid set found within budget" (honest failure), or
  (b) silently return an invalid/incomplete adjustment set (dangerous failure)?

This matters because a governance tool that returns a wrong causal
explanation under thermal stress -- without saying so -- is worse than one
that says "insufficient compute, escalate" during exactly the conditions
(SCAR_LOCK) when something is already going wrong.

Verified result (this session): correctly returns None at max_size=1.
FULL (max_size=3): {'Z1', 'Z2'}
THROTTLE (max_size=2): {'Z1', 'Z2'}
SCAR_LOCK (max_size=1): None  -- honest, not a guess.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixed_causal import CausalDAG, find_valid_backdoor_set

# Anti-vacuity: --sabotage forces find_valid_backdoor_set to return a wrong
# single-variable set at SCAR_LOCK. The gate below must then exit 1. If this
# flag ever produces exit 0, the gate has stopped working and every PASS it
# has ever printed is uninformative.
if "--sabotage" in sys.argv:
    _real = find_valid_backdoor_set
    def find_valid_backdoor_set(dag, t, y, max_size=3):
        if max_size == 1:
            return {'Z1'}
        return _real(dag, t, y, max_size=max_size)
    print("[SABOTAGE MODE] SCAR_LOCK forced to return {'Z1'} -- gate must exit 1.")

# Construct a DAG where the ONLY valid backdoor set has size 2
# (no single variable suffices) -- this forces max_size=1 (SCAR_LOCK level)
# to fail, and we check HOW it fails.
dag = CausalDAG()
for n in ['Z1', 'Z2', 'T', 'Y']:
    dag.add_node(n)
dag.add_edge('Z1', 'T')
dag.add_edge('Z2', 'T')
dag.add_edge('Z1', 'Y')
dag.add_edge('Z2', 'Y')
# Neither Z1 alone nor Z2 alone blocks both confounding paths -- need both.

result_full = find_valid_backdoor_set(dag, 'T', 'Y', max_size=3)
result_throttle = find_valid_backdoor_set(dag, 'T', 'Y', max_size=2)
result_scarlock = find_valid_backdoor_set(dag, 'T', 'Y', max_size=1)

print("=== TEST 2: Honest failure under throttling ===")
print(f"FULL budget (max_size=3):     {result_full}")
print(f"THROTTLE budget (max_size=2): {result_throttle}")
print(f"SCAR_LOCK budget (max_size=1): {result_scarlock}")

print(f"\nAt SCAR_LOCK, does it silently return a WRONG single-variable set,")
print(f"or correctly return None (I don't have enough budget to find a valid")
print(f"explanation)? Result: {'CORRECTLY RETURNS None (honest)' if result_scarlock is None else 'DANGER: returned ' + str(result_scarlock) + ' -- verify this is actually valid!'}")

if result_scarlock is not None:
    # If it did return something, verify it's ACTUALLY valid, don't trust the label
    backdoor_dag = CausalDAG()
    backdoor_dag.nodes = set(dag.nodes)
    backdoor_dag.edges = [(p, c) for p, c in dag.edges if p != 'T']
    is_actually_valid = backdoor_dag.d_separated('T', 'Y', result_scarlock)
    print(f"Double-checking validity directly: {is_actually_valid}")

# ---------------------------------------------------------------------------
# VERDICT GATE.
#
# Until 2026-08-14 this script had no assert, no raise and no sys.exit. It
# computed the right answer, printed "DANGER: returned ... " when the answer
# was wrong, verified independently that it was wrong -- and then exited 0.
# A test named honest_failure was honest about failure and reported success.
# That is a third defect category beyond Type A (no fail path) and Type B
# (unreachable fail path): the check DOES compute the correct verdict and
# then discards it. Detection without consequence.
#
# The gate below is demonstrated to return both verdicts. Run with
# --sabotage to force the wrong-answer branch and confirm exit 1.
# ---------------------------------------------------------------------------
expected_full = {'Z1', 'Z2'}
failures = []
if result_full != expected_full:
    failures.append(f"FULL budget should recover {expected_full}, got {result_full}")
if result_throttle != expected_full:
    failures.append(f"THROTTLE budget should recover {expected_full}, got {result_throttle}")
if result_scarlock is not None:
    failures.append(
        f"SCAR_LOCK returned {result_scarlock} instead of None. The DAG is built "
        f"so that no single variable blocks both confounding paths, so any "
        f"single-variable answer here is a silent wrong explanation under "
        f"throttle -- exactly the failure this test exists to catch.")

print()
if failures:
    print("VERDICT: FAIL")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("VERDICT: PASS -- honest None at SCAR_LOCK, correct set at FULL and THROTTLE.")
sys.exit(0)
