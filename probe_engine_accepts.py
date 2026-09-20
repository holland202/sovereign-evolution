#!/usr/bin/env python3
"""
probe_engine_accepts.py — does the Evidence Engine have an accepting branch?

WHY THIS EXISTS
---------------
tests/test_evidence_engine.py is 11/11 and wired into CI at b126c0e. Every
one of those 11 asserts that the engine REFUSES something. Reading
verdicts.py, every return path in authorize_verdict is also a refusal:
unpinned revision -> VOID, incomplete evidence -> VOID, otherwise
NOT_ADMISSIBLE with supported/refuted/admissible hardcoded False. Its own
reason string says "numerical criterion evaluation not implemented in v0.1".

If that reading is right, the suite passes because a function that always
refuses satisfies every test asserting refusal — a gate proven in one
direction only. That is the Type A shape, in the evidence engine, in the
repo built to account for evidence.

This probe tries to refute that reading. It is written to be WRONG if an
accepting branch exists anywhere.

Run from the repo root (needs `import sovereign_ops`):
    python3 probe_engine_accepts.py
    python3 probe_engine_accepts.py --sabotage   # anti-vacuity, must exit 1

Exit codes
----------
0  probe ran, every prediction resolved, verdicts printed
1  a prediction was REFUTED, or --sabotage detected (both are correct outcomes
   for their mode) — see the verdict block
2  could not run (import failure, engine shape not as expected)

REGISTERED BEFORE RUNNING
-------------------------
QUAL-1  The probe can build a manifest + evidence that the engine itself
        classifies as COMPLETE (evidence.is_complete() is True) with a pinned
        revision. If it cannot, it never reached the branch in question and
        P1 is VOID rather than confirmed.

P1      With COMPLETE evidence and a pinned revision, authorize_verdict still
        returns admissible=False, supported=False, refuted=False.
        FALSIFIABLE: any True there refutes it and the engine discriminates.

P2      Static: no VerdictRecord constructed anywhere in sovereign_ops/ sets
        supported, refuted, reproduced or admissible to True.
        FALSIFIABLE: one such construction refutes it.

P3      sigkill_cause returns the same value for every input tested, i.e. its
        branch cannot change the result. FALSIFIABLE: any differing return.

P4      UNRUN. CLAIMS.md records SE-001 as SUPPORTED with SE-RSI-001 as its
        evidence. No code in this repo derives SUPPORTED. Once criterion
        evaluation exists, does the derived verdict agree with the hand-typed
        status? Not answerable today and no number here bears on it.

SCOPE: this is a finding about the ENGINE's v0.1 completeness, not about
SE-RSI-001, which is a complete and correct experiment record.
"""

import argparse
import ast
import os
import sys

PKG = "sovereign_ops"


def fail(msg, code=2):
    print(f"could not run: {msg}", file=sys.stderr)
    sys.exit(code)


def build_complete_case(schemas, evidence_mod):
    """Smallest well-formed COMPLETE case: pinned SHA, all arms done, exit 0."""
    manifest = schemas.ExperimentManifest(
        experiment_id="PROBE-COMPLETE-001",
        claim_id="PROBE-001",
        instrument=schemas.InstrumentRef(
            repository="holland202/quasar",
            revision="061368f1eb6a776dc824c03255026928d4c533d7",
        ),
        status=schemas.ExperimentStatus.COMPLETE,
        seeds_test_block="TEST-9001-9008",
        budget_work_units=720,
        arms=["arm_a", "arm_b"],
        primary_metrics=["delta"],
        acceptance=schemas.AcceptanceCriteria(),
    )
    ev = evidence_mod.build_evidence_from_observation(
        evidence_id="EV-PROBE-COMPLETE-001",
        experiment_id="PROBE-COMPLETE-001",
        exit_code=0,
        signal=None,
        completed_arms=["arm_a", "arm_b"],
        registered_arms=["arm_a", "arm_b"],
        artifact_path="probe.log",
    )
    return manifest, ev


def scan_verdict_records(pkg_dir):
    """P2: every VerdictRecord(...) construction, and its boolean keywords."""
    flags = ("supported", "refuted", "reproduced", "admissible")
    sites = []
    for fn in sorted(os.listdir(pkg_dir)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(pkg_dir, fn)
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except SyntaxError as e:
            sites.append((fn, 0, {"UNPARSEABLE": str(e)}))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "VerdictRecord":
                continue
            vals = {}
            for kw in node.keywords:
                if kw.arg in flags:
                    v = kw.value
                    vals[kw.arg] = (v.value if isinstance(v, ast.Constant)
                                    else f"<{type(v).__name__}>")
            sites.append((fn, node.lineno, vals))
    return sites


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sabotage", action="store_true",
                    help="inject an accepting branch; the probe must notice")
    args = ap.parse_args()

    try:
        from sovereign_ops import schemas, evidence as evidence_mod, verdicts
    except Exception as e:
        fail(f"{type(e).__name__}: {e} (run from the repo root)")

    pkg_dir = os.path.dirname(schemas.__file__)

    print("=" * 72)
    print("PROBE — DOES THE EVIDENCE ENGINE HAVE AN ACCEPTING BRANCH?")
    print("=" * 72)
    print(f"package  : {pkg_dir}")
    print(f"python   : {sys.version.split()[0]}  platform={sys.platform}")
    print(f"sabotage : {args.sabotage}")
    print()

    authorize = verdicts.authorize_verdict
    if args.sabotage:
        # Anti-vacuity: an engine that DOES accept. If the probe still reports
        # P1 CONFIRMED against this, the probe is inert and proves nothing.
        def authorize(manifest, ev, _real=verdicts.authorize_verdict):
            v = _real(manifest, ev)
            if ev.is_complete():
                return schemas.VerdictRecord(
                    experiment_id=manifest.experiment_id,
                    status=schemas.VerdictStatus.SUPPORTED,
                    supported=True, refuted=False, reproduced=False,
                    admissible=True,
                    reason="INJECTED accepting branch (sabotage)",
                )
            return v

    # -- QUAL-1 ------------------------------------------------------------
    print("-- QUAL-1  can the probe reach the branch at all? " + "-" * 23)
    try:
        manifest, ev = build_complete_case(schemas, evidence_mod)
    except Exception as e:
        fail(f"manifest/evidence construction failed: {type(e).__name__}: {e}")
    pinned = manifest.is_revision_pinned()
    complete = ev.is_complete()
    print(f"  revision pinned          : {pinned}          EXPECTED True")
    print(f"  evidence.is_complete()   : {complete}          EXPECTED True")
    print(f"  completeness             : {ev.completeness.value}")
    print(f"  missing_arms             : {ev.missing_arms}")
    qual1 = pinned and complete
    print(f"  QUAL-1 {'OK' if qual1 else 'FAIL'}")
    if not qual1:
        print("\n  The probe never reached the branch under test. P1 is VOID,")
        print("  not confirmed. Nothing below is a finding about the engine.")
        print("=" * 72)
        return 1
    print()

    # -- P1 ----------------------------------------------------------------
    print("-- P1  dynamic: is a COMPLETE case still refused? " + "-" * 23)
    v = authorize(manifest, ev)
    print(f"  status      : {v.status.value}")
    print(f"  supported   : {v.supported}")
    print(f"  refuted     : {v.refuted}")
    print(f"  reproduced  : {v.reproduced}")
    print(f"  admissible  : {v.admissible}")
    print(f"  reason      : {v.reason}")
    accepts = bool(v.supported or v.refuted or v.admissible)
    p1 = not accepts
    print(f"  P1 -> {'CONFIRMED (no accepting branch reached)' if p1 else 'REFUTED (engine accepted)'}")
    print()

    # -- P2 ----------------------------------------------------------------
    print("-- P2  static: any VerdictRecord built with a True flag? " + "-" * 15)
    sites = scan_verdict_records(pkg_dir)
    if not sites:
        print("  no VerdictRecord constructions found — engine shape unexpected")
        print("  P2 VOID")
        p2 = None
    else:
        any_true = False
        for fn, lineno, vals in sites:
            trues = [k for k, val in vals.items() if val is True]
            if trues:
                any_true = True
            print(f"  {fn}:{lineno}  {vals}"
                  + (f"   <-- TRUE: {trues}" if trues else ""))
        p2 = not any_true
        print(f"  {len(sites)} construction site(s)")
        print(f"  P2 -> {'CONFIRMED (none set a True flag)' if p2 else 'REFUTED'}")
    print()

    # -- P3 ----------------------------------------------------------------
    print("-- P3  is sigkill_cause's branch decorative? " + "-" * 27)
    cases = [(137, "SIGKILL"), (137, None), (0, None), (1, "SIGTERM"),
             (None, None), (9, "sigkill"), (255, "OOM")]
    outs = []
    for code, sig in cases:
        r = verdicts.sigkill_cause(code, sig)
        outs.append(r)
        print(f"  exit={str(code):>4}  signal={str(sig):>8}  -> {r}")
    distinct = sorted(set(outs))
    p3 = len(distinct) == 1
    print(f"  distinct return values: {distinct}")
    print(f"  P3 -> {'CONFIRMED (constant; the branch cannot change it)' if p3 else 'REFUTED'}")
    print()

    # -- P4 ----------------------------------------------------------------
    print("-- P4  REGISTERED, NOT RUN " + "-" * 45)
    print("  CLAIMS.md records SE-001 SUPPORTED with SE-RSI-001 as evidence.")
    print("  No code here derives SUPPORTED. Once criterion evaluation exists,")
    print("  does the derived verdict agree with the hand-typed status?")
    print("  STATUS: NOT VALIDATED. No number above bears on it.")
    print()

    # -- verdict -----------------------------------------------------------
    print("=" * 72)
    if args.sabotage:
        ok = (p1 is False)
        print("SABOTAGE MODE: an accepting branch was injected.")
        print(f"  probe reported P1 {'REFUTED — it noticed (correct)' if ok else 'CONFIRMED — IT IS INERT'}")
        print("=" * 72)
        return 1 if ok else 2

    print("SCOPE: a finding about the ENGINE's v0.1 completeness. SE-RSI-001 is")
    print("a complete, correct experiment record and nothing here reflects on it.")
    print(f"  P1 {'CONFIRMED' if p1 else 'REFUTED'}"
          f"   P2 {'CONFIRMED' if p2 else ('VOID' if p2 is None else 'REFUTED')}"
          f"   P3 {'CONFIRMED' if p3 else 'REFUTED'}   P4 UNRUN")
    if p1 and p2:
        print("\n  authorize_verdict has no reachable accepting branch. The 11/11")
        print("  suite passes because every test asserts refusal and every path")
        print("  refuses. The gate is proven in one direction only.")
    print("=" * 72)
    return 0 if (p1 and p2 is not False) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
