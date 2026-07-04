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
