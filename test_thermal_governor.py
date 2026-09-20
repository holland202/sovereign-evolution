#!/usr/bin/env python3
"""
test_thermal_governor.py — asserting suite for the thermal governor.

The hysteresis bug in the source survived because nothing exercised it: the
__main__ block read the live device once and printed. A single reading cannot
detect a hysteresis fault, which is by definition about the transition
between two readings. This drives sequences through an injected reader, so
the logic is testable off-device.

    python3 test_thermal_governor.py             # expect exit 0
    python3 test_thermal_governor.py --sabotage  # expect exit 1

Stdlib only.
"""

import argparse
import sys

import thermal_governor as tg
from thermal_governor import (
    CALIBRATION_ZONES, DEADBAND, THRESHOLDS, ThermalGovernor, ThermalMode,
)

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def gov_from(seq):
    """Governor fed a scripted sequence of peak temps."""
    box = {"i": 0}

    def reader():
        t = seq[min(box["i"], len(seq) - 1)]
        box["i"] += 1
        return [("thermal_zone0", t)]
    return ThermalGovernor(reader=reader)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sabotage", action="store_true",
                    help="neuter the deadband; hysteresis tests must fail")
    args = ap.parse_args()

    if args.sabotage:
        tg.DEADBAND = 0.0
        print("SABOTAGE: DEADBAND = 0.0 — hysteresis tests must now fail\n")

    print("== classification bands ==")
    c = ThermalGovernor._classify_temp
    check("30.0 -> UNRESTRICTED", c(30.0) is ThermalMode.UNRESTRICTED)
    check("39.0 -> CAUTION", c(39.0) is ThermalMode.CAUTION)
    check("41.0 -> THROTTLE", c(41.0) is ThermalMode.THROTTLE)
    check("49.0 -> SEVERE", c(49.0) is ThermalMode.SEVERE)
    check("55.7 -> CRITICAL", c(55.7) is ThermalMode.CRITICAL,
          "the peak seen in an SLC v12 screenshot")

    print("\n== FIX-1  escalation is immediate ==")
    g = gov_from([30.0, 55.0])
    g.read()
    s = g.read()
    check("30 -> 55 escalates at once", s.mode is ThermalMode.CRITICAL,
          f"mode={s.mode.value}")
    check("CRITICAL is not governable", not s.governable)

    print("\n== FIX-1  de-escalation waits for the deadband ==")
    g = gov_from([49.0, 47.0])
    g.read()                                   # SEVERE
    s = g.read()                               # 47.0, above 48.0-1.5
    check("SEVERE holds at 47.0 (floor is 46.5)",
          s.mode is ThermalMode.SEVERE,
          f"mode={s.mode.value} — this is the bug the source shipped")
    g = gov_from([49.0, 46.0])
    g.read()
    s = g.read()
    check("SEVERE releases at 46.0 (below floor)",
          s.mode is not ThermalMode.SEVERE, f"mode={s.mode.value}")

    print("\n== FIX-1  boundary is exclusive, not sloppy ==")
    floor = THRESHOLDS[ThermalMode.SEVERE] - DEADBAND
    g = gov_from([49.0, floor])
    g.read()
    s = g.read()
    check(f"exactly at the floor ({floor}) still holds",
          s.mode is ThermalMode.SEVERE, f"mode={s.mode.value}")

    print("\n== FIX-2  no fabricated readings when blind ==")
    g = ThermalGovernor(reader=lambda: [])
    s = g.read()
    check("data_available is False", s.data_available is False)
    check("peak_temp is None, not 35.0", s.peak_temp is None, f"{s.peak_temp}")
    check("avg_temp is None, not 35.0", s.avg_temp is None, f"{s.avg_temp}")
    check("still fail-open (governable)", s.governable)
    d = s.to_dict()
    check("to_dict exposes the blindness", d["data_available"] is False
          and d["peak_temp"] is None)

    print("\n== FIX-3  zone selection is explicit ==")
    both = [("thermal_zone0", 36.0), ("thermal_zone9", 70.7)]
    g_all = ThermalGovernor(reader=lambda: both)
    g_cal = ThermalGovernor(reader=lambda: [z for z in both
                                            if z[0] in CALIBRATION_ZONES])
    s_all, s_cal = g_all.read(), g_cal.read()
    check("all-zones peak picks the compute zone",
          s_all.peak_temp == 70.7, f"{s_all.peak_temp}")
    check("calibration subset picks the skin zone",
          s_cal.peak_temp == 36.0, f"{s_cal.peak_temp}")
    check("the two zone sets disagree on MODE",
          s_all.mode is not s_cal.mode,
          f"{s_all.mode.value} vs {s_cal.mode.value}")
    check("state records which zones were read",
          s_cal.zones_read == ("thermal_zone0",), str(s_cal.zones_read))

    print("\n== FIX-4  dead threshold is gone ==")
    check("UNRESTRICTED has no threshold entry",
          ThermalMode.UNRESTRICTED not in THRESHOLDS)
    check("governor has no _hysteresis_active field",
          not hasattr(ThermalGovernor(reader=lambda: []), "_hysteresis_active"))

    print("\n== ANTI-VACUITY: the governor returns more than one mode ==")
    g = gov_from([30.0, 39.0, 41.0, 49.0, 55.0])
    seen = {g.read().mode for _ in range(5)}
    check("at least four distinct modes observed", len(seen) >= 4,
          f"{sorted(m.value for m in seen)}")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\n" + "=" * 68)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if args.sabotage:
        if failed:
            print("SABOTAGE detected: " + ", ".join(failed[:3]))
            print("The suite can fail. Its passes mean something.")
            return 1
        print("SABOTAGE NOT DETECTED — this suite is vacuous.")
        return 2
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All assertions passed.")
    print("Scope: thresholds 38.0/40.5/48.0/52.0 are carried from the source")
    print("labelled 'calibrated'. No calibration record exists. UNVERIFIED.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:                                  # noqa: BLE001
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
