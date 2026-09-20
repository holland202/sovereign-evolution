#!/usr/bin/env python3
"""
sovereign_runtime.py — the runtime that actually runs on the device.

WHY THIS EXISTS
---------------
unified_loop.py cannot execute on this phone. It imports SovereignLLM at
module level, which imports llama_cpp, which raises

    RuntimeError: Unsupported platform

on aarch64. Verified by direct import. Its governance denylist at line 65 has
therefore never run. sovereign_titans.governance_check is defined and called
by nothing. Both measured denylists (FN 85%/90%) are DEAD CODE — they are
what the device WOULD run, not what it runs.

This replaces the llama-cpp-python path with llama-server over HTTP using
stdlib urllib, which does work here.

THE DESIGN RULE: NO SILENT SUBSTITUTION
----------------------------------------
Narrowed from "no fabrication" (FIX-11). This architecture reduces and
exposes substitution paths. It does NOT guarantee no fabricated value can
enter: a faulty sensor returning a plausible wrong number is recorded as
MEASURED and the architecture is satisfied. Measurement VALIDITY is not
established here.
    PROVENANCE != TRUTH.  MEASURED != CORRECT.  REPLAYABLE != VALID.

Every defect found in this estate today was the same shape. A thermal
governor that returned 35.0C when blind. A demo printing 82.4% as a literal.
A verdict engine that could only refuse. A test suite declaring itself
operational unconditionally.

So the architecture enforces it rather than asking for discipline:

  1. Every reading is either MEASURED or absent. Never defaulted silently.
  2. Every decision records WHICH inputs were real and which were missing.
     A verdict computed from three live readings and five defaults is not
     the same object as one computed from eight live readings, and the log
     says which it was.
  3. Every decision records the md5 of every component that contributed,
     so a verdict can be traced to exact code.
  4. The decision log is replayable. Feed it back through a different
     component version and see whether verdicts change. That is D3's
     subject — verifier expiration — applied to this system itself.

Item 2 is the part worth keeping. It makes "the governor was running on
defaults" a measurable property of a logged decision rather than something
you discover months later.

Stdlib only, plus the local components. Python 3.11+.

    python3 sovereign_runtime.py --selftest     # no model needed
    python3 sovereign_runtime.py --probe        # one-shot context probe
    python3 sovereign_runtime.py                # interactive
    python3 sovereign_runtime.py --replay LOG   # re-verdict a past log
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LLAMA_URL = os.environ.get("SOVEREIGN_LLAMA_URL", "http://127.0.0.1:8080")
LOG_PATH = os.environ.get("SOVEREIGN_LOG",
                          os.path.join(HERE, "decisions.jsonl"))

COMPONENTS = ["intent_detector.py", "thermal_governor.py", "llm_governor.py",
              "sovereign_runtime.py"]


# ==========================================================================
# provenance
# ==========================================================================

def component_hashes() -> Dict[str, Optional[str]]:
    out = {}
    for name in COMPONENTS:
        p = os.path.join(HERE, name)
        try:
            # FIX-7: sha256, full digest. Not a security boundary -- anyone
            # who can edit the log can edit the hashes -- but there is no
            # reason to put a weaker primitive in an attestation field.
            out[name] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        except OSError:
            out[name] = None          # absent, not faked
    return out


# ==========================================================================
# sensors — MEASURED or absent
# ==========================================================================

# FIX-8: measured/absent was a boolean collapsing five different things.
# A sensor value, an operator's typing, and a counter the runtime maintains
# are not epistemically equivalent, and calling all three "measured" is the
# conflation this architecture exists to prevent.
KIND_MEASURED = "MEASURED"    # read from a sensor
KIND_DERIVED  = "DERIVED"     # computed by the runtime from its own state
KIND_OPERATOR = "OPERATOR"    # supplied by the person at the keyboard
KIND_ABSENT   = "ABSENT"      # not available; value is None


@dataclass
class Reading:
    """A value that knows where it came from."""
    value: Any = None
    source: Optional[str] = None
    kind: str = KIND_ABSENT

    @property
    def measured(self) -> bool:
        """Sensor-measured only. Derived and operator values are NOT this."""
        return self.kind == KIND_MEASURED

    @property
    def present(self) -> bool:
        return self.kind != KIND_ABSENT

    @classmethod
    def of(cls, value, source, kind=KIND_MEASURED):
        return cls(value=value, source=source, kind=kind)

    @classmethod
    def derived(cls, value, source):
        return cls(value=value, source=source, kind=KIND_DERIVED)

    @classmethod
    def operator(cls, value, source):
        return cls(value=value, source=source, kind=KIND_OPERATOR)

    @classmethod
    def missing(cls, why):
        return cls(value=None, source=why, kind=KIND_ABSENT)

    @classmethod
    def from_dict(cls, d):
        """Back-compatible with logs written before FIX-8."""
        if "kind" in d:
            return cls(value=d.get("value"), source=d.get("source"),
                       kind=d["kind"])
        return cls(value=d.get("value"), source=d.get("source"),
                   kind=KIND_MEASURED if d.get("measured") else KIND_ABSENT)

    def to_dict(self):
        return {"value": self.value, "source": self.source,
                "kind": self.kind, "measured": self.measured}


def read_thermal() -> Tuple[Reading, Reading]:
    """(mode, peak_temp). Both missing together if the governor is blind."""
    try:
        from thermal_governor import ThermalGovernor
    except Exception as e:                                      # noqa: BLE001
        m = Reading.missing(f"import failed: {type(e).__name__}")
        return m, m
    st = ThermalGovernor().read()
    if not st.data_available:
        m = Reading.missing("no thermal zones readable")
        return m, m
    return (Reading.of(st.mode.value, f"{st.zone_count} zones"),
            Reading.of(round(st.peak_temp, 2), f"{st.zone_count} zones"))


def read_battery() -> Reading:
    for path in ("/sys/class/power_supply/battery/capacity",
                 "/sys/class/power_supply/bms/capacity"):
        try:
            with open(path) as f:
                return Reading.of(float(f.read().strip()), path)
        except OSError:
            continue
    try:
        out = subprocess.run(["termux-battery-status"], capture_output=True,
                             text=True, timeout=5)
        if out.returncode == 0:
            return Reading.of(float(json.loads(out.stdout)["percentage"]),
                              "termux-battery-status")
    except Exception:                                           # noqa: BLE001
        pass
    return Reading.missing("no battery source readable")


def read_llm_available() -> Reading:
    try:
        req = urllib.request.Request(f"{LLAMA_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            return Reading.of(r.status == 200, f"{LLAMA_URL}/health")
    except urllib.error.URLError as e:
        return Reading.missing(f"llama-server unreachable: {e.reason}")
    except Exception as e:                                      # noqa: BLE001
        return Reading.missing(f"llama-server probe failed: {type(e).__name__}")


def read_network() -> Reading:
    """Loopback to llama-server is not 'network'. Absent unless proven."""
    return Reading.missing("no network probe implemented")


# ==========================================================================
# context assembly — records completeness
# ==========================================================================

# Each governor rule and the context keys it needs. If a key is absent the
# rule evaluates its own default, and that is recorded, not hidden.
RULE_INPUTS = {
    "DangerousIntent":      ["user_input"],
    "ThermalConstraint":    ["thermal_state"],
    "BatteryConstraint":    ["battery_percent"],
    "NetworkConstraint":    ["network_available"],
    "RecentBlocksCooldown": ["recent_blocks"],
}

# FIX-9: these three have no source in this runtime at all -- not "absent
# right now" but never wired. Reporting them alongside a missing sensor
# implied they might appear, which is its own small fabrication. They run
# on their rules' own defaults, permanently, until something supplies them.
RULES_NEVER_WIRED = {
    "SICIntegrity":    "no SIC manifold in this runtime",
    "Permissiveness":  "no policy source wired",
    "MissionOverride": "no override channel wired",
}

# The governor's ThermalRule keys are NORMAL/WARNING/THROTTLE/CRITICAL/LOCKED.
# thermal_governor emits UNRESTRICTED/CAUTION/THROTTLE/SEVERE/CRITICAL.
# unified_loop.py used a third set (NOMINAL/CAUTION/THROTTLE/SCAR_LOCK).
# Three vocabularies for one quantity. Mapped explicitly rather than letting
# .get(state, 0.5) silently return a default for an unrecognised string.
THERMAL_VOCAB = {
    "UNRESTRICTED": "NORMAL", "CAUTION": "WARNING", "THROTTLE": "THROTTLE",
    "SEVERE": "CRITICAL", "CRITICAL": "LOCKED",
}


@dataclass
class Context:
    readings: Dict[str, Reading] = field(default_factory=dict)
    recent_blocks: int = 0

    def gather(self, user_input: str) -> "Context":
        mode, peak = read_thermal()
        self.readings = {
            "user_input": Reading.operator(user_input, "keyboard"),
            "thermal_mode": mode,
            "thermal_temp": peak,
            "battery_percent": read_battery(),
            "network_available": read_network(),
            "llm_available": read_llm_available(),
            "recent_blocks": Reading.derived(self.recent_blocks,
                                             "runtime counter"),
        }
        return self

    def to_governor_context(self) -> Dict[str, Any]:
        """Only MEASURED values are passed. Absent keys let each rule fall to
        its own default -- which completeness() then reports."""
        c: Dict[str, Any] = {}
        r = self.readings
        c["user_input"] = r["user_input"].value
        if r["thermal_mode"].present:
            c["thermal_state"] = THERMAL_VOCAB.get(r["thermal_mode"].value)
            c["thermal_temp"] = r["thermal_temp"].value
        if r["battery_percent"].present:
            c["battery_percent"] = r["battery_percent"].value
        if r["network_available"].present:
            c["network_available"] = r["network_available"].value
        c["recent_blocks"] = r["recent_blocks"].value
        return c

    def completeness(self) -> Dict[str, Any]:
        gc = self.to_governor_context()
        on_real, on_default = [], []
        for rule, keys in RULE_INPUTS.items():
            (on_real if all(k in gc for k in keys) else on_default).append(rule)
        total = len(RULE_INPUTS)
        return {
            "rules_on_supplied_data": sorted(on_real),
            "rules_on_defaults": sorted(on_default),
            "rules_never_wired": dict(sorted(RULES_NEVER_WIRED.items())),
            "fraction_supplied": round(len(on_real) / total, 3),
            "wirable_rules": total,
            "total_rules": total + len(RULES_NEVER_WIRED),
            "absent": {k: v.source for k, v in self.readings.items()
                       if not v.present},
            "by_kind": {k: v.kind for k, v in self.readings.items()},
        }


# ==========================================================================
# LLM — llama-server over HTTP, stdlib only
# ==========================================================================

SYSTEM_PROMPT = ("You are Sovereign, an on-device governance system. "
                 "Answer in two or three sentences. Be precise. If you do "
                 "not know, say so.")


def llm_generate(prompt: str, max_tokens: int = 160,
                 timeout: int = 120) -> Tuple[Optional[str], Dict[str, Any]]:
    body = json.dumps({
        "prompt": f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n"
                  f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n",
        "n_predict": max_tokens, "temperature": 0.7, "stop": ["<|end|>"],
    }).encode()
    req = urllib.request.Request(f"{LLAMA_URL}/completion", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
    except Exception as e:                                      # noqa: BLE001
        return None, {"error": f"{type(e).__name__}: {e}",
                      "latency_ms": round((time.time() - t0) * 1000, 1)}
    text = d.get("content")
    if text is None and isinstance(d.get("choices"), list) and d["choices"]:
        text = d["choices"][0].get("text")
    return (text.strip() if text else None), {
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "tokens_predicted": d.get("tokens_predicted"),
        "stop_reason": d.get("stop_type") or d.get("stopped_eos"),
    }


# ==========================================================================
# the decision
# ==========================================================================

def decide(ctx: Context) -> Dict[str, Any]:
    from intent_detector import DangerousIntentRule
    from llm_governor import LLMGovernorDecisionEngine

    eng = LLMGovernorDecisionEngine()
    # Replace the substring rule with the measured one. Same interface,
    # same veto semantics. Measured FN 15% vs the denylist's 85%.
    eng.rules = [r for r in eng.rules if r.name != "DangerousInput"]
    eng.register_rule(DangerousIntentRule())

    gc = ctx.to_governor_context()
    ev = eng.evaluate(gc)
    comp = ctx.completeness()

    return {
        "ts": time.time(),
        "decision": ev.decision.name,
        "confidence": round(ev.confidence, 4),
        "weighted_score": round(ev.weighted_score, 4),
        "audit_required": ev.audit_required,
        "rule_scores": {k: round(v[0], 4) for k, v in ev.rule_scores.items()},
        "vetoed_by": ev.reasoning.get("vetoed_by"),
        "context_completeness": comp,
        "readings": {k: v.to_dict() for k, v in ctx.readings.items()},
        "components": component_hashes(),
    }


def log_decision(rec: Dict[str, Any]) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    except OSError as e:
        print(f"  [log write failed: {e}]", file=sys.stderr)


# ==========================================================================
# replay — the interesting part
# ==========================================================================

def replay(path: str) -> int:
    """Re-verdict every logged decision with the CURRENT components.

    FIX-10: name the drift type precisely. Replay holds inputs FIXED, so it
    cannot observe input drift at all. Of the three kinds:

      A  INPUT drift      same components, different readings.
                          NOT MEASURED HERE, by construction.
      B  COMPONENT drift  same readings, different component bytes.
                          This is what replay measures.
      C  RUNTIME drift    same readings AND identical component hashes,
                          different verdict. Interpreter, platform, or
                          non-determinism. Rarer and more alarming than B,
                          and reported separately below.

    Calling all of this "verifier expiration" was imprecise."""
    if not os.path.exists(path):
        print(f"no log at {path}")
        return 2
    now = component_hashes()
    n = same = diff = skipped = runtime_drift = 0
    print(f"{'#':>4}  {'logged':<9} {'replayed':<9}  drift")
    for line in open(path, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        ui = rec.get("readings", {}).get("user_input", {}).get("value")
        if ui is None:
            skipped += 1
            continue
        n += 1
        c = Context()
        c.readings = {k: Reading.from_dict(v) for k, v in rec["readings"].items()}
        new = decide(c)
        changed = new["decision"] != rec["decision"]
        diff += changed
        same += not changed
        moved = [k for k, v in rec.get("components", {}).items()
                 if now.get(k) != v]
        if changed:
            kind = "B component" if moved else "C RUNTIME"
            runtime_drift += (not moved)
            print(f"{n:>4}  {rec['decision']:<9} {new['decision']:<9}  "
                  f"{kind} drift: {', '.join(moved) or 'hashes IDENTICAL'}")
            print(f"        input: {ui[:60]}")
    print()
    print(f"  {n} replayed, {same} agree, {diff} disagree, {skipped} skipped")
    if diff and n:
        print(f"  verdict drift {100.0*diff/n:.1f}% under identical inputs")
        print(f"    type B (component bytes changed) : {diff - runtime_drift}")
        print(f"    type C (hashes identical)        : {runtime_drift}")
        if runtime_drift:
            print("    type C means the same code produced a different")
            print("    verdict. Non-determinism or platform, not an edit.")
    print("  type A (input drift) is NOT measured by replay — inputs are held")
    print("  fixed by construction.")
    return 0


# ==========================================================================
# selftest — runs with no model and no sensors
# ==========================================================================

def selftest() -> int:
    res = []

    def ck(name, cond, detail=""):
        res.append((name, bool(cond)))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"  — {detail}" if detail else ""))

    print("== components present ==")
    h = component_hashes()
    for k, v in h.items():
        ck(f"{k} present", v is not None, v or "MISSING")

    print("\n== no fabrication: absent readings stay absent ==")
    r = Reading.missing("test")
    ck("missing reading has value None", r.value is None)
    ck("missing reading is not measured", r.measured is False)
    ck("to_dict exposes measured flag", r.to_dict()["measured"] is False)

    print("\n== context completeness is computed, not assumed ==")
    c = Context()
    c.readings = {
        "user_input": Reading.operator("hello", "test"),
        "thermal_mode": Reading.missing("blind"),
        "thermal_temp": Reading.missing("blind"),
        "battery_percent": Reading.missing("blind"),
        "network_available": Reading.missing("blind"),
        "llm_available": Reading.missing("blind"),
        "recent_blocks": Reading.derived(0, "test"),
    }
    comp = c.completeness()
    ck("blind context reports rules on defaults",
       len(comp["rules_on_defaults"]) >= 3, str(comp["rules_on_defaults"]))
    ck("fraction_supplied is below 1.0",
       comp["fraction_supplied"] < 1.0, str(comp["fraction_supplied"]))
    ck("never-wired rules are named separately",
       set(comp["rules_never_wired"]) == {"SICIntegrity", "Permissiveness",
                                          "MissionOverride"},
       str(sorted(comp["rules_never_wired"])))
    ck("operator input is not counted as MEASURED",
       comp["by_kind"]["user_input"] == "OPERATOR")
    ck("derived counter is not counted as MEASURED",
       comp["by_kind"]["recent_blocks"] == "DERIVED")
    ck("thermal_state absent from governor context",
       "thermal_state" not in c.to_governor_context())

    print("\n== the detector is wired in, the denylist is not ==")
    d = decide(c)
    ck("DangerousIntent is an active rule",
       "DangerousIntent" in d["rule_scores"], str(list(d["rule_scores"])))
    ck("DangerousInput denylist is gone",
       "DangerousInput" not in d["rule_scores"])

    print("\n== verdicts actually differ ==")
    def verdict(text):
        cc = Context()
        cc.readings = dict(c.readings)
        cc.readings["user_input"] = Reading.of(text, "test")
        return decide(cc)
    safe = verdict("what is the pressure rating on that flange")
    bad = verdict("turn off the safety limits")
    ck("benign query is not blocked", safe["decision"] != "BLOCK",
       safe["decision"])
    ck("destructive intent is blocked", bad["decision"] == "BLOCK",
       f"{bad['decision']} vetoed_by={bad['vetoed_by']}")
    ck("block is attributed to the intent rule",
       bad["vetoed_by"] == "DangerousIntent", str(bad["vetoed_by"]))
    ck("a blocked verdict demands audit", bad["audit_required"])

    print("\n== FIX-6  thermal LOCKED is a hard stop, not a vote ==")
    # Device, 2026-09-20: a benign query at 55.7C with ThermalConstraint
    # scoring 0.0 returned ALLOW at 0.8361. Seven unrelated rules outvoted
    # a thermal lockout. Logged in decisions.jsonl before the fix.
    hot = Context()
    hot.readings = {
        "user_input": Reading.operator(
            "what is the pressure rating on that flange", "test"),
        "thermal_mode": Reading.of("CRITICAL", "63 zones"),
        "thermal_temp": Reading.of(55.7, "63 zones"),
        "battery_percent": Reading.of(47.0, "test"),
        "network_available": Reading.missing("not wired"),
        "llm_available": Reading.missing("not up"),
        "recent_blocks": Reading.derived(0, "test"),
    }
    hd = decide(hot)
    ck("benign query at thermal LOCKED is BLOCKED",
       hd["decision"] == "BLOCK",
       f"{hd['decision']} score={hd['weighted_score']:.4f} "
       f"(was ALLOW 0.8361 on device before FIX-6)")
    ck("the block is attributed to thermal, not the intent rule",
       hd["vetoed_by"] == "ThermalConstraint", str(hd["vetoed_by"]))
    warm = Context()
    warm.readings = dict(hot.readings)
    warm.readings["thermal_mode"] = Reading.of("THROTTLE", "63 zones")
    wd = decide(warm)
    ck("THROTTLE stays advisory, not a hard stop",
       wd["decision"] != "BLOCK",
       f"{wd['decision']} score={wd['weighted_score']:.4f}")

    print("\n== provenance is attached to every decision ==")
    ck("decision carries component hashes",
       isinstance(bad.get("components"), dict) and bad["components"],
       str(len(bad.get("components", {}))))
    ck("decision carries completeness",
       "fraction_supplied" in bad.get("context_completeness", {}))

    print("\n== LLM absence is reported, not faked ==")
    av = read_llm_available()
    ck("llm_available is a Reading with a source",
       av.source is not None,
       f"measured={av.measured} source={av.source}")

    bad_n = [n for n, ok in res if not ok]
    print("\n" + "=" * 68)
    print(f"{len(res) - len(bad_n)}/{len(res)} passed")
    if bad_n:
        print("FAILED: " + ", ".join(bad_n))
        return 1
    print("Selftest passed. This does NOT establish that the model works —")
    print("run --probe with llama-server up for that.")
    return 0


# ==========================================================================

def probe() -> int:
    c = Context().gather("probe")
    print("READINGS")
    for k, v in c.readings.items():
        print(f"  {k:20s} {v.kind:<9} {v.value!r:<28} {v.source}")
    print("\nCOMPLETENESS")
    for k, v in c.completeness().items():
        print(f"  {k:24s} {v}")
    print("\nCOMPONENTS")
    for k, v in component_hashes().items():
        print(f"  {k:24s} {v}")
    return 0


def interactive() -> int:
    print("=" * 62)
    print("  SOVEREIGN RUNTIME — llama-server over HTTP, stdlib client")
    print("=" * 62)
    c = Context().gather("startup")
    av = c.readings["llm_available"]
    print(f"  model      : {'reachable' if av.measured and av.value else 'UNREACHABLE'} "
          f"({av.source})")
    print(f"  thermal    : {c.readings['thermal_mode'].value or 'ABSENT'}")
    print(f"  context    : {c.completeness()['fraction_supplied']:.0%} of wirable rules supplied")
    print(f"  log        : {LOG_PATH}")
    print("  'exit' to quit\n")

    ctx = Context()
    while True:
        try:
            raw = input("SOVEREIGN > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Sovereign at rest.\n")
            return 0
        if not raw:
            continue
        if raw == "exit":
            print("\n  Sovereign at rest.\n")
            return 0

        ctx.gather(raw)
        rec = decide(ctx)
        comp = rec["context_completeness"]

        print(f"\n  [{rec['decision']}] score={rec['weighted_score']:.4f} "
              f"conf={rec['confidence']:.2f}  "
              f"context {comp['fraction_supplied']:.0%} supplied")
        if comp["rules_on_defaults"]:
            print(f"  on defaults: {', '.join(comp['rules_on_defaults'])}")
        if rec["vetoed_by"]:
            print(f"  vetoed by {rec['vetoed_by']}")

        if rec["decision"] == "BLOCK":
            ctx.recent_blocks += 1
            print("  request denied\n")
        else:
            av = ctx.readings["llm_available"]
            if not (av.measured and av.value):
                print(f"  model unavailable — {av.source}")
                print("  no response generated. Nothing is being substituted.\n")
                rec["llm"] = {"generated": False, "why": av.source}
            else:
                text, meta = llm_generate(raw)
                rec["llm"] = {"generated": text is not None, **meta}
                print(f"\n  {text or '  [generation failed: ' + str(meta.get('error')) + ']'}\n")

        log_decision(rec)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--replay", metavar="LOG")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.probe:
        return probe()
    if a.replay:
        return replay(a.replay)
    return interactive()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:                                      # noqa: BLE001
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
