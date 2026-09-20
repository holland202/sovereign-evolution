#!/usr/bin/env python3
"""
thermal_governor.py — 16-zone Schmitt-trigger thermal governor

Ported from thermal_governor_FIXED.py (Drive, 2026-07-02, 6027 bytes).

CARRIED FROM THE SOURCE
-----------------------
FIX-1  hysteresis was a no-op. The original _apply_hysteresis ignored
       peak_temp and returned raw_mode unconditionally; DEADBAND was defined
       and never consulted, so de-escalation was instant. Verified there by
       direct test: dropping from SEVERE to 47.0C -- above the 46.5C deadband
       floor -- de-escalated to THROTTLE immediately.

NEW IN THIS PORT
----------------
FIX-2  no more fabricated readings. The source returned avg_temp=35.0,
       peak_temp=35.0, governable=True when it could read no zones, and
       to_dict() emitted those as ordinary floats. A consumer could not tell
       an invented 35.0 from a measured one. Here temps are None when there
       is no data and `data_available` is explicit. Fail-open is kept -- a
       blind governor should not halt the pipeline -- but it now says it is
       blind instead of inventing a comfortable number.

FIX-3  zone selection is explicit. The source globbed every
       /sys/class/thermal/thermal_zone*/temp and took max(). On this device
       that pulls in compute zones that run far hotter than skin sensors,
       while calibrate_governance.py probes only zones 0, 1, 2, 4, 7.
       Two components on the same phone were reading different things and
       calling both "temperature". Zones are now a constructor argument, the
       chosen set is reported in the state, and probe_zone_disagreement()
       measures the gap rather than assuming it.

FIX-4  dead code removed: THRESHOLDS[UNRESTRICTED] = 31.0 was never read
       (_classify_temp falls through to UNRESTRICTED, and de-escalation
       cannot reach index 0), and _hysteresis_active was set once and never
       used. Both are gone; the threshold table now holds only live values.

FIX-5  the reader is injectable, so hysteresis is testable off-device
       instead of only on hardware.

NOT ADDRESSED
-------------
The thresholds (38.0 / 40.5 / 48.0 / 52.0) are labelled "Calibrated --
Snapdragon SM8750" in the source. No calibration record accompanies them.
They are carried forward unchanged and their provenance is UNVERIFIED.

Stdlib only. Python 3.11+.
"""

from __future__ import annotations

import glob
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Sequence, Tuple

__all__ = ["ThermalMode", "ThermalState", "ThermalGovernor",
           "THRESHOLDS", "DEADBAND", "CALIBRATION_ZONES",
           "read_thermal", "thermal_gate", "probe_zone_disagreement"]


class ThermalMode(Enum):
    UNRESTRICTED = "UNRESTRICTED"
    CAUTION = "CAUTION"
    THROTTLE = "THROTTLE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


MODE_ORDER = [ThermalMode.UNRESTRICTED, ThermalMode.CAUTION,
              ThermalMode.THROTTLE, ThermalMode.SEVERE, ThermalMode.CRITICAL]

# Carried unchanged from the source. Provenance UNVERIFIED — see docstring.
# FIX-4: UNRESTRICTED has no entry; it is the fall-through, not a threshold.
THRESHOLDS = {
    ThermalMode.CAUTION: 38.0,
    ThermalMode.THROTTLE: 40.5,
    ThermalMode.SEVERE: 48.0,
    ThermalMode.CRITICAL: 52.0,
}

DEADBAND = 1.5   # Schmitt trigger hysteresis, °C

# The subset calibrate_governance.py probes. FIX-3.
CALIBRATION_ZONES = ("thermal_zone0", "thermal_zone1", "thermal_zone2",
                     "thermal_zone4", "thermal_zone7")


@dataclass
class ThermalState:
    mode: ThermalMode
    avg_temp: Optional[float]
    peak_temp: Optional[float]
    zone_count: int
    timestamp: float
    governable: bool
    data_available: bool          # FIX-2
    zones_read: Tuple[str, ...] = ()

    def to_dict(self):
        return {
            "mode": self.mode.value,
            "avg_temp": round(self.avg_temp, 2) if self.avg_temp is not None else None,
            "peak_temp": round(self.peak_temp, 2) if self.peak_temp is not None else None,
            "zone_count": self.zone_count,
            "timestamp": self.timestamp,
            "governable": self.governable,
            "data_available": self.data_available,
            "zones_read": list(self.zones_read),
        }


def _read_sysfs(zone_filter: Optional[Sequence[str]]) -> List[Tuple[str, float]]:
    zones = []
    for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
        name = os.path.basename(os.path.dirname(path))
        if zone_filter is not None and name not in zone_filter:
            continue
        try:
            with open(path) as f:
                temp = int(f.read().strip()) / 1000.0
        except (IOError, OSError, ValueError):
            continue
        if -10 < temp < 200:          # reject disconnected sensors
            zones.append((name, temp))
    return zones


class ThermalGovernor:
    def __init__(self,
                 zone_filter: Optional[Sequence[str]] = None,
                 reader: Optional[Callable[[], List[Tuple[str, float]]]] = None):
        """zone_filter=None reads every zone (the source's behaviour).
        Pass CALIBRATION_ZONES to match calibrate_governance.py.
        reader is injectable for testing (FIX-5)."""
        self._last_mode = ThermalMode.UNRESTRICTED
        self._zone_filter = zone_filter
        self._reader = reader or (lambda: _read_sysfs(self._zone_filter))

    def read_zones(self) -> List[Tuple[str, float]]:
        return self._reader()

    @staticmethod
    def _classify_temp(temp: float) -> ThermalMode:
        if temp >= THRESHOLDS[ThermalMode.CRITICAL]:
            return ThermalMode.CRITICAL
        if temp >= THRESHOLDS[ThermalMode.SEVERE]:
            return ThermalMode.SEVERE
        if temp >= THRESHOLDS[ThermalMode.THROTTLE]:
            return ThermalMode.THROTTLE
        if temp >= THRESHOLDS[ThermalMode.CAUTION]:
            return ThermalMode.CAUTION
        return ThermalMode.UNRESTRICTED

    def _apply_hysteresis(self, raw_mode: ThermalMode, peak_temp: float) -> ThermalMode:
        """FIX-1. Escalate immediately; de-escalate only after cooling a full
        DEADBAND below the threshold that put us in the CURRENT mode."""
        cur = MODE_ORDER.index(self._last_mode)
        new = MODE_ORDER.index(raw_mode)

        if new >= cur:                      # hotter or same — act now
            self._last_mode = raw_mode
            return raw_mode

        floor = THRESHOLDS.get(self._last_mode)
        if floor is None or peak_temp < (floor - DEADBAND):
            self._last_mode = raw_mode
            return raw_mode

        return self._last_mode              # held hot: not cooled enough

    def read(self) -> ThermalState:
        zones = self.read_zones()

        if not zones:
            # FIX-2: blind, and says so. Fail-open, but no invented numbers.
            return ThermalState(
                mode=ThermalMode.CAUTION, avg_temp=None, peak_temp=None,
                zone_count=0, timestamp=time.time(), governable=True,
                data_available=False, zones_read=())

        temps = [t for _, t in zones]
        peak = max(temps)
        mode = self._apply_hysteresis(self._classify_temp(peak), peak)

        return ThermalState(
            mode=mode, avg_temp=sum(temps) / len(temps), peak_temp=peak,
            zone_count=len(zones), timestamp=time.time(),
            governable=(mode is not ThermalMode.CRITICAL),
            data_available=True, zones_read=tuple(n for n, _ in zones))

    def gate(self) -> Tuple[bool, ThermalState]:
        state = self.read()
        return state.governable, state


def probe_zone_disagreement() -> dict:
    """FIX-3. Read the same instant two ways and report the gap."""
    all_z = _read_sysfs(None)
    cal_z = _read_sysfs(CALIBRATION_ZONES)
    g = ThermalGovernor
    out = {
        "all_zones_count": len(all_z),
        "cal_zones_count": len(cal_z),
        "all_peak": max((t for _, t in all_z), default=None),
        "cal_peak": max((t for _, t in cal_z), default=None),
        "hottest_zone": max(all_z, key=lambda z: z[1])[0] if all_z else None,
    }
    out["all_mode"] = g._classify_temp(out["all_peak"]).value if all_z else None
    out["cal_mode"] = g._classify_temp(out["cal_peak"]).value if cal_z else None
    out["delta_c"] = (round(out["all_peak"] - out["cal_peak"], 2)
                      if all_z and cal_z else None)
    out["modes_disagree"] = (out["all_mode"] != out["cal_mode"]
                             if all_z and cal_z else None)
    return out


_governor = ThermalGovernor()


def read_thermal() -> ThermalState:
    return _governor.read()


def thermal_gate() -> Tuple[bool, ThermalState]:
    return _governor.gate()


if __name__ == "__main__":
    st = ThermalGovernor().read()
    print(f"Mode:       {st.mode.value}")
    print(f"Data:       {'available' if st.data_available else 'UNAVAILABLE'}")
    print(f"Avg temp:   {st.avg_temp if st.avg_temp is None else f'{st.avg_temp:.1f}°C'}")
    print(f"Peak temp:  {st.peak_temp if st.peak_temp is None else f'{st.peak_temp:.1f}°C'}")
    print(f"Zones:      {st.zone_count}")
    print(f"Governable: {st.governable}")
    print()
    print("Zone-set disagreement (FIX-3):")
    for k, v in probe_zone_disagreement().items():
        print(f"  {k:18s} {v}")
