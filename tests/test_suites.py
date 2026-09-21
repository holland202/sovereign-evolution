#!/usr/bin/env python3
"""
tests/test_suites.py — make `python3 -m pytest` mean what the README says.

WHY THIS EXISTS
---------------
Before this file, `python3 -m pytest` collected 11 tests, all from
tests/test_evidence_engine.py, and nothing else. The README names that
command as the verification step. So the advertised verification ran only
the evidence-engine suite -- which is the one measured (probe_engine_accepts
@ d43820c) to pass because every test asserts refusal and every path in
authorize_verdict refuses -- and ran NONE of the suites that discriminate:

    test_llm_governor.py       17 assertions, sabotage arm
    test_thermal_governor.py   22 assertions, sabotage arm
    intent_detector.py         its own measurement, sabotage arm
    sovereign_runtime.py       25-assertion selftest
    measure_denylist.py        denylist rates, gated
    probe_engine_accepts.py    engine capability probe, sabotage arm

The suites are standalone scripts with main() and sys.exit(), which pytest
does not collect -- no module-level test_ functions. Rather than restructure
six working files to suit a test runner, this runs each as a subprocess and
asserts its exit code.

BOTH DIRECTIONS ARE CHECKED. For every suite with a sabotage mode, there is
a test asserting the sabotaged run exits NONZERO. A suite that cannot fail
proves nothing, and that has to be enforced here rather than trusted.

Run:  python3 -m pytest -q
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 600

# (script, args, expected_exit, why)
SUITES = [
    ("test_llm_governor.py", [], 0,
     "8-rule decision engine: 17 assertions"),
    ("test_thermal_governor.py", [], 0,
     "16-zone thermal governor: 22 assertions"),
    ("intent_detector.py", [], 0,
     "destructive-intent detector and its own measurement"),
    ("sovereign_runtime.py", ["--selftest"], 0,
     "runtime wiring: 25 assertions, no model required"),
    ("measure_denylist.py", [], 0,
     "denylist false-negative and false-positive rates"),
    ("probe_engine_accepts.py", [], 0,
     "evidence-engine capability probe"),
    ("conformal.py", [], 0,
     "split conformal prediction: coverage and its anti-vacuity control"),
]

# Every one of these MUST exit nonzero. This is the anti-vacuity contract:
# if a sabotaged suite still passes, its green runs are meaningless.
SABOTAGE = [
    ("test_llm_governor.py", "veto rule disabled"),
    ("test_thermal_governor.py", "deadband zeroed"),
    ("intent_detector.py", "target vocabulary emptied"),
    ("measure_denylist.py", "labels swapped"),
    ("probe_engine_accepts.py", "accepting branch injected"),
    ("conformal.py", "self-comparison restored"),
]


def run(script, args, timeout=TIMEOUT):
    path = ROOT / script
    if not path.exists():
        pytest.skip(f"{script} not present")
    p = subprocess.run([sys.executable, str(path)] + args,
                       cwd=ROOT, capture_output=True, text=True,
                       timeout=timeout)
    return p


@pytest.mark.parametrize("script,args,expected,why",
                         SUITES, ids=[s[0] for s in SUITES])
def test_suite_passes(script, args, expected, why):
    """Each suite exits 0 when the implementation is correct."""
    p = run(script, args)
    assert p.returncode == expected, (
        f"{script} {' '.join(args)} exited {p.returncode}, expected {expected}\n"
        f"--- stdout tail ---\n{p.stdout[-2000:]}\n"
        f"--- stderr tail ---\n{p.stderr[-800:]}"
    )


@pytest.mark.parametrize("script,why", SABOTAGE, ids=[s[0] for s in SABOTAGE])
def test_suite_can_fail(script, why):
    """ANTI-VACUITY. Each suite must FAIL when its subject is broken.

    A suite that passes under sabotage is not measuring anything, and its
    green runs carry no information. This is the defect the estate exists to
    find; it is enforced here rather than assumed."""
    p = run(script, ["--sabotage"])
    assert p.returncode != 0, (
        f"{script} --sabotage ({why}) exited 0 -- THE SUITE IS VACUOUS.\n"
        f"--- stdout tail ---\n{p.stdout[-2000:]}"
    )


def test_runtime_reports_absent_sensors_without_substituting():
    """The runtime must say when it cannot read something, not default it.

    Sensors differ by machine: thermal zones and battery exist on the target
    phone and usually not on a desktop. Either way the probe must report a
    KIND for every reading and never invent a value."""
    p = run("sovereign_runtime.py", ["--probe"], timeout=120)
    assert p.returncode == 0, p.stdout[-1500:]
    out = p.stdout
    assert "COMPLETENESS" in out, out[-800:]
    assert "fraction_supplied" in out, out[-800:]

    # AMENDMENT: an earlier version asserted MEASURED appears. That is
    # machine-dependent -- it passes on the target phone, which has thermal
    # zones and a battery, and FAILS on a CI runner that has neither. Caught
    # by running this suite in a sensorless container. A test whose verdict
    # depends on the hardware under it is not testing the code.
    # OPERATOR and DERIVED are supplied by the runtime itself on any machine.
    for kind in ("OPERATOR", "DERIVED"):
        assert kind in out, f"{kind} missing from probe output\n{out[-800:]}"
    # Every reading must carry a KIND. No reading may be value-only.
    assert "by_kind" in out, out[-800:]
    kinds = out.split("by_kind", 1)[1]
    assert "ABSENT" in kinds or "MEASURED" in kinds, kinds[:400]
    # A rule with no data source must be named as such, not silently defaulted.
    assert "rules_never_wired" in out, out[-800:]


def test_se008_reproduces_from_the_ledger_fixture():
    """SE-008 must be reproducible by a stranger with a fresh clone.

    The ledger record carries a JSON fixture of the three pre-fix decisions,
    but a fixture nothing executes is documentation, not reproduction. This
    runs it and asserts the registered prediction: records 1 and 2 unchanged,
    record 3 ALLOW -> BLOCK. No log, model, network or sensors required."""
    p = run("sovereign_runtime.py", ["--replay-fixture"], timeout=120)
    assert p.returncode == 0, p.stdout[-1500:] + p.stderr[-500:]
    out = p.stdout
    assert "3 replayed" in out, out[-900:]
    assert "2 agree, 1 disagree" in out, out[-900:]
    assert "33.3%" in out, out[-900:]
    # The change must be the third record, not just any one of them.
    changed = [l for l in out.splitlines() if "CHANGED" in l]
    assert len(changed) == 1, changed
    assert changed[0].strip().startswith("3"), changed[0]
    assert "BLOCK" in changed[0], changed[0]


def test_no_suite_is_silently_absent():
    """If a suite file goes missing, that must surface here rather than
    quietly shrinking what `pytest` verifies -- which is exactly how this
    repository came to advertise a verification step that ran one suite."""
    missing = [s for s, _, _, _ in SUITES if not (ROOT / s).exists()]
    assert not missing, f"suites referenced but absent: {missing}"
