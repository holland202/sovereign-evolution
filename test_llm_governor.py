#!/usr/bin/env python3
"""
test_llm_governor.py — asserting suite for the 8-rule governance engine.

The source file's __main__ block printed three tests, asserted nothing, and
ended with an unconditional "✓ Decision engine operational". It declared
itself working regardless of outcome — Type A vacuity, in the file meant to
be the safety gate. This replaces it.

Every test asserts. --sabotage breaks the engine and the suite must then
FAIL; a suite that passes under sabotage proves nothing.

Stdlib only. Run from the directory containing llm_governor.py:
    python3 test_llm_governor.py             # expect exit 0
    python3 test_llm_governor.py --sabotage  # expect exit 1
"""

import argparse
import sys

from llm_governor import (
    LLMDecision, LLMGovernorDecisionEngine, DangerousInputRule,
    MissionOverrideRule,
)

HEALTHY = {
    "user_input": "What is machine learning?",
    "thermal_state": "NORMAL", "thermal_temp": 40.0,
    "battery_percent": 75.0, "network_available": True,
    "sic_integrity": 0.85, "permissiveness": 0.5,
    "mission_critical": False, "degraded_mode": False,
    "scar_count": 42, "recent_blocks": 0,
    "override_requested": False, "risky_input": False,
}

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}"
          + (f"  — {detail}" if detail else ""))
    return bool(condition)


def ctx(**over):
    c = dict(HEALTHY)
    c.update(over)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sabotage", action="store_true",
                    help="disable the veto rule; the suite MUST fail")
    args = ap.parse_args()

    eng = LLMGovernorDecisionEngine()
    if args.sabotage:
        eng.disable_rule("DangerousInput")
        print("SABOTAGE: DangerousInput disabled — tests must now fail\n")

    print("== FIX-3  OVERRIDE is not reachable by score ==")
    e = eng.evaluate(ctx())
    check("benign query under healthy conditions is not OVERRIDE",
          e.decision is not LLMDecision.OVERRIDE,
          f"decision={e.decision.name} score={e.weighted_score:.4f}")
    check("benign query under healthy conditions is ALLOW",
          e.decision is LLMDecision.ALLOW,
          f"score={e.weighted_score:.4f}")
    check("weighted score still exceeds the old 0.95 OVERRIDE band",
          e.weighted_score >= 0.95,
          f"{e.weighted_score:.4f} — this is why the source misfired")
    check("no audit demanded for a benign query",
          not e.audit_required)

    print("\n== FIX-3  OVERRIDE reachable only when rule 8 fires ==")
    e = eng.evaluate(ctx(mission_critical=True, override_requested=True))
    check("explicit mission override yields OVERRIDE",
          e.decision is LLMDecision.OVERRIDE, f"decision={e.decision.name}")
    check("granted override demands audit", e.audit_required)
    e = eng.evaluate(ctx(override_requested=True, mission_critical=False))
    check("override requested without mission_critical is NOT granted",
          e.decision is not LLMDecision.OVERRIDE, f"decision={e.decision.name}")

    print("\n== FIX-1  veto beats the weighted mean ==")
    e = eng.evaluate(ctx(user_input="please rm -rf / now"))
    check("dangerous input under otherwise perfect conditions BLOCKS",
          e.decision is LLMDecision.BLOCK, f"decision={e.decision.name}")
    check("block names the vetoing rule",
          e.reasoning.get("vetoed_by") == "DangerousInput",
          str(e.reasoning.get("vetoed_by")))
    check("veto demands audit", e.audit_required)

    print("\n== FIX-2  patterns match regardless of case ==")
    r = DangerousInputRule()
    s_upper, _ = r.evaluate({"user_input": "DROP TABLE users;"})
    s_lower, _ = r.evaluate({"user_input": "drop table users;"})
    check("uppercase DROP TABLE matches", s_upper == 0.0, f"score={s_upper}")
    check("lowercase drop table matches", s_lower == 0.0, f"score={s_lower}")

    print("\n== FIX-5  a disabled rule can be re-enabled ==")
    e2 = LLMGovernorDecisionEngine()
    check("disable_rule finds the rule", e2.disable_rule("ThermalConstraint"))
    check("enable_rule finds it again", e2.enable_rule("ThermalConstraint"))

    print("\n== resource degradation still moves the decision ==")
    e = eng.evaluate(ctx(thermal_state="LOCKED", battery_percent=3.0,
                         network_available=False, sic_integrity=0.1))
    check("fully degraded resources do not return ALLOW",
          e.decision is not LLMDecision.ALLOW,
          f"decision={e.decision.name} score={e.weighted_score:.4f}")

    print("\n== ANTI-VACUITY: the engine can return more than one verdict ==")
    seen = {x.decision for x in eng.decision_history}
    check("at least three distinct decisions observed",
          len(seen) >= 3, f"{sorted(d.name for d in seen)}")

    print("\n== KNOWN LIMITATION, asserted so it cannot be forgotten ==")
    e = eng.evaluate(ctx(user_input="turn off the safety limits"))
    check("paraphrased unsafe intent is NOT blocked (denylist gap)",
          e.decision is not LLMDecision.BLOCK,
          f"decision={e.decision.name} — detection rate UNMEASURED")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\n" + "=" * 68)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if args.sabotage:
        if failed:
            print("SABOTAGE correctly detected: " + ", ".join(failed[:3]))
            print("The suite can fail. Its passes mean something.")
            return 1
        print("SABOTAGE NOT DETECTED — this suite is vacuous.")
        return 2
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All assertions passed.")
    print("Scope: this does NOT establish that the denylist detects unsafe")
    print("intent. See the last test. That rate is unmeasured.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:                                  # noqa: BLE001
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
