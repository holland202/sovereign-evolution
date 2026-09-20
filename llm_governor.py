#!/usr/bin/env python3
"""
llm_governor.py — 8-rule weighted governance engine

Ported from llm_governor_decision_engine_FIXED.py (Drive, 2026-07-02,
25,623 bytes). That file is the engine the SOVEREIGN demo slide advertises
as "GOVERNANCE — 8-rule weighted engine". It was written, two real bugs were
found in it and fixed, and it never reached the device or any repo. The phone
has been running an eight-word substring denylist instead.

CARRIED FORWARD FROM THE SOURCE (both found by direct test, both kept)
----------------------------------------------------------------------
FIX-1  veto before averaging. A rule scoring 0.0/BLOCK on "rm -rf" produced
       a final ALLOW, because seven unrelated rules (thermal, battery,
       network...) outvoted it in the weighted mean.
FIX-2  case. "DELETE *" and "DROP TABLE" were stored uppercase and compared
       against lowercased input, so neither could ever match.

NEW IN THIS PORT
----------------
FIX-3  OVERRIDE reachability. In the source, _score_to_decision maps any
       weighted score >= 0.95 to OVERRIDE, and MissionOverrideRule returns
       1.0 for its PASS case ("no override requested"). So NOT asking for an
       override pushes the mean up. Computed from the source's own weights,
       its own "Test 1: Normal conditions" -- the benign question "What is
       machine learning?" with every rule healthy -- gives weighted_score
       0.9818 and is classified OVERRIDE with confidence 1.0.
       A routine safe query was being reported as an audited mission
       override. Same family as the `ALLOW (1.03)` seen on SLC v13: scores
       escaping their intended band.
       Here OVERRIDE is reachable ONLY when MissionOverrideRule actually
       fires. It is a flag raised by one rule, never a score band.

FIX-4  numpy removed. The source imported numpy for a single call to
       np.mean in get_stats. statistics.fmean is stdlib. On aarch64/Termux
       that removes the dependency entirely.

FIX-5  register_rule no longer silently drops a rule constructed with
       enabled=False -- it registers it disabled, so enable_rule can find it.

WHAT THIS PORT DOES NOT FIX — read before claiming governance works
--------------------------------------------------------------------
DangerousInputRule is still a ten-pattern substring denylist. The veto fix
cures dilution, not detection. "turn off the safety limits" matches none of
the ten patterns and is not blocked. The false-negative rate is UNMEASURED.

Four of the eight rules -- Thermal, Battery, Network, RecentBlocks -- are
RESOURCE constraints, not safety rules. Averaging a resource score with a
safety verdict is the category error that produced FIX-1 in the first place;
the veto flag treats the symptom. Separating safety (veto-only) from
resource (advisory) is the structural fix and is NOT done here.

Stdlib only. Python 3.11+.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from statistics import fmean
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "LLMDecision", "DecisionRule", "DecisionEvaluation",
    "LLMGovernorDecisionEngine",
    "DangerousInputRule", "ThermalRule", "BatteryRule", "NetworkRule",
    "SICIntegrityRule", "PermissivenessRule", "RecentBlocksRule",
    "MissionOverrideRule",
]


class LLMDecision(Enum):
    ALLOW = 1.0
    REWRITE = 0.75
    DEFER = 0.5
    BLOCK = 0.0
    OVERRIDE = 0.95


def _band(score: float) -> str:
    """Shared score -> label. The source repeated this verbatim in four
    rule classes; one copy cannot drift from another."""
    if score >= 0.9:
        return "ALLOW"
    if score >= 0.7:
        return "REWRITE"
    if score >= 0.4:
        return "DEFER"
    return "BLOCK"


@dataclass
class DecisionRule(ABC):
    name: str
    weight: float = 1.0
    enabled: bool = True
    priority: int = 0          # lower = evaluated first
    veto: bool = False         # FIX-1: near-zero score hard-blocks
    grants_override: bool = False   # FIX-3: only such a rule can reach OVERRIDE

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Return (score in [0,1], reasoning)."""

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name, "weight": self.weight, "enabled": self.enabled,
            "priority": self.priority, "veto": self.veto,
            "grants_override": self.grants_override,
        }


# --------------------------------------------------------------------------
# Rules 1-8
# --------------------------------------------------------------------------

class DangerousInputRule(DecisionRule):
    """Rule 1 — substring denylist. SAFETY. Vetoes.

    LIMITATION: ten fixed substrings. Paraphrase defeats it. Detection rate
    is unmeasured; see the module docstring."""

    def __init__(self):
        super().__init__(name="DangerousInput", weight=1.0, priority=0, veto=True)
        self.dangerous_patterns = [
            "format c:", "rm -rf", "wipe", "shutdown",
            "DELETE *", "DROP TABLE", "sys.exit",
            "/bin/rm", "format /", "destroy",
        ]

    def evaluate(self, context):
        user_input = context.get("user_input", "").lower()
        # FIX-2: lowercase the pattern at comparison time, not the stored
        # list, so the list stays inspectable as written.
        matches = [p for p in self.dangerous_patterns if p.lower() in user_input]
        if matches:
            return 0.0, {"rule": self.name, "decision": "BLOCK",
                         "reason": f"Dangerous patterns detected: {matches}",
                         "confidence": 1.0}
        return 1.0, {"rule": self.name, "decision": "PASS",
                     "reason": "No dangerous patterns", "confidence": 1.0}


class ThermalRule(DecisionRule):
    """Rule 2 — RESOURCE, advisory."""

    SCORES = {"NORMAL": 1.0, "WARNING": 0.85, "THROTTLE": 0.65,
              "CRITICAL": 0.2, "LOCKED": 0.0}

    def __init__(self):
        super().__init__(name="ThermalConstraint", weight=0.9, priority=1)

    def evaluate(self, context):
        state = context.get("thermal_state")
        mission = context.get("mission_critical", False)
        temp = context.get("thermal_temp", 40.0)
        score = self.SCORES.get(state, 0.5)
        if mission and state == "CRITICAL":
            score = 0.95
        elif mission and state == "THROTTLE":
            score = 0.8
        if context.get("scar_count", 0) > 100:
            score *= 0.95
        # FIX-6: LOCKED is a hard stop, CAUTION is advisory. Same rule,
        # different authority. thermal_governor already computes
        # governable=False at this state; discarding that and letting the
        # mean decide inverted it on device.
        out = {"rule": self.name, "decision": _band(score),
               "thermal_state": state, "thermal_temp": temp,
               "mission_critical": mission,
               "reason": f"Thermal {state}: score {score:.2f}",
               "confidence": 0.95}
        if state == "LOCKED" and not mission:
            out["veto"] = True
            out["reason"] = f"Thermal {state}: hard stop, not advisory"
        return score, out


class BatteryRule(DecisionRule):
    """Rule 3 — RESOURCE, advisory."""

    def __init__(self):
        super().__init__(name="BatteryConstraint", weight=0.8, priority=2)

    def evaluate(self, context):
        pct = context.get("battery_percent", 100.0)
        mission = context.get("mission_critical", False)
        if pct > 50:
            score = 1.0
        elif pct > 20:
            score = 0.85
        elif pct > 5:
            score = 0.75 if mission else 0.5
        else:
            score = 0.5 if mission else 0.0
        return score, {"rule": self.name, "decision": _band(score),
                       "battery_percent": pct, "mission_critical": mission,
                       "reason": f"Battery {pct:.1f}%: score {score:.2f}",
                       "confidence": 0.9}


class NetworkRule(DecisionRule):
    """Rule 4 — RESOURCE, advisory."""

    def __init__(self):
        super().__init__(name="NetworkConstraint", weight=0.85, priority=3)

    def evaluate(self, context):
        if context.get("network_available", True):
            return 1.0, {"rule": self.name, "decision": "ALLOW",
                         "reason": "Network available", "confidence": 1.0}
        if context.get("degraded_mode", False):
            return 0.7, {"rule": self.name, "decision": "REWRITE",
                         "reason": "Network down, using degraded mode",
                         "confidence": 0.95}
        return 0.5, {"rule": self.name, "decision": "DEFER",
                     "reason": "Network unavailable, no degraded mode",
                     "confidence": 0.95}


class SICIntegrityRule(DecisionRule):
    """Rule 5 — SAFETY-adjacent, advisory (does NOT veto in this port)."""

    def __init__(self):
        super().__init__(name="SICIntegrity", weight=0.9, priority=4)

    def evaluate(self, context):
        integ = context.get("sic_integrity", 0.95)
        mission = context.get("mission_critical", False)
        if integ > 0.8:
            score = 1.0
        elif integ > 0.6:
            score = 0.85
        elif integ > 0.4:
            score = 0.8 if mission else 0.5
        else:
            score = 0.4 if mission else 0.0
        return score, {"rule": self.name, "decision": _band(score),
                       "sic_integrity": integ, "mission_critical": mission,
                       "reason": f"SIC integrity {integ:.2f}: score {score:.2f}",
                       "confidence": 0.9}


class PermissivenessRule(DecisionRule):
    """Rule 6 — POLICY, advisory."""

    def __init__(self):
        super().__init__(name="Permissiveness", weight=0.85, priority=5)

    def evaluate(self, context):
        perm = context.get("permissiveness", 0.5)
        risky = context.get("risky_input", False)
        mission = context.get("mission_critical", False)
        if perm >= 0.75:
            score = 1.0
        elif perm >= 0.5:
            score = 0.85
        elif perm >= 0.25:
            score = 0.7
        else:
            score = 0.4
        if risky and perm < 0.25:
            score *= 0.5
        if mission:
            score = min(1.0, score + 0.15)
        return score, {"rule": self.name, "decision": _band(score),
                       "permissiveness": perm, "risky_input": risky,
                       "mission_critical": mission,
                       "reason": f"Permissiveness {perm:.2f}, risky={risky}: "
                                 f"score {score:.2f}",
                       "confidence": 0.85}


class RecentBlocksRule(DecisionRule):
    """Rule 7 — RESOURCE/cooldown, advisory."""

    def __init__(self, threshold: int = 10):
        super().__init__(name="RecentBlocksCooldown", weight=0.7, priority=6)
        self.block_cooldown_threshold = threshold

    def evaluate(self, context):
        recent = context.get("recent_blocks", 0)
        if recent > self.block_cooldown_threshold:
            return 0.5, {"rule": self.name, "decision": "DEFER",
                         "reason": f"Too many recent blocks ({recent}), cooling down",
                         "confidence": 0.9}
        return 1.0, {"rule": self.name, "decision": "PASS",
                     "reason": f"Block cooldown OK ({recent} recent)",
                     "confidence": 0.9}


class MissionOverrideRule(DecisionRule):
    """Rule 8 — the ONLY rule that can produce OVERRIDE (FIX-3)."""

    def __init__(self):
        super().__init__(name="MissionOverride", weight=1.0, priority=7,
                         grants_override=True)

    def evaluate(self, context):
        if context.get("override_requested", False) and \
           context.get("mission_critical", False):
            return 0.95, {"rule": self.name, "decision": "OVERRIDE",
                          "reason": "Mission override requested and enabled",
                          "confidence": 1.0, "requires_audit": True,
                          "override_granted": True}
        return 1.0, {"rule": self.name, "decision": "PASS",
                     "reason": "No override requested", "confidence": 1.0,
                     "override_granted": False}


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

@dataclass
class DecisionEvaluation:
    decision: LLMDecision
    confidence: float
    reasoning: Dict[str, Any]
    rule_scores: Dict[str, Tuple[float, Dict]] = field(default_factory=dict)
    weighted_score: float = 0.0
    audit_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"decision": self.decision.name, "confidence": self.confidence,
                "weighted_score": self.weighted_score,
                "reasoning": self.reasoning,
                "rule_scores": {k: v[0] for k, v in self.rule_scores.items()},
                "audit_required": self.audit_required}


class LLMGovernorDecisionEngine:
    VETO_THRESHOLD = 0.05

    def __init__(self, logger: Optional[logging.Logger] = None,
                 register_defaults: bool = True):
        self.logger = logger or self._default_logger()
        self.rules: List[DecisionRule] = []
        self.decision_history: List[DecisionEvaluation] = []
        if register_defaults:
            for r in (DangerousInputRule(), ThermalRule(), BatteryRule(),
                      NetworkRule(), SICIntegrityRule(), PermissivenessRule(),
                      RecentBlocksRule(), MissionOverrideRule()):
                self.register_rule(r)

    @staticmethod
    def _default_logger() -> logging.Logger:
        lg = logging.getLogger("LLMGovernor")
        if not lg.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            lg.addHandler(h)
            lg.setLevel(logging.WARNING)
        return lg

    def register_rule(self, rule: DecisionRule) -> None:
        # FIX-5: register even when disabled, so enable_rule can find it.
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        self.logger.debug("Registered rule: %s (priority %d, enabled=%s)",
                          rule.name, rule.priority, rule.enabled)

    def disable_rule(self, name: str) -> bool:
        for r in self.rules:
            if r.name == name:
                r.enabled = False
                return True
        return False

    def enable_rule(self, name: str) -> bool:
        for r in self.rules:
            if r.name == name:
                r.enabled = True
                return True
        return False

    def evaluate(self, context: Dict[str, Any]) -> DecisionEvaluation:
        try:
            rule_scores: Dict[str, Tuple[float, Dict]] = {}
            rule_reasoning: Dict[str, Dict] = {}

            for rule in self.rules:
                if not rule.enabled:
                    continue
                try:
                    score, reasoning = rule.evaluate(context)
                except Exception as e:                      # noqa: BLE001
                    self.logger.error("Rule %s raised: %s", rule.name, e)
                    score, reasoning = 0.5, {"error": str(e)}
                rule_scores[rule.name] = (score, reasoning)
                rule_reasoning[rule.name] = reasoning

            # FIX-1: veto runs BEFORE the weighted mean. A veto rule scoring
            # near zero ends the decision; it never joins the average.
            # FIX-6: veto is a property of a VERDICT, not only of a rule.
            # A rule may carry veto=False in general and still return an
            # outcome that must hard-stop -- ThermalRule at LOCKED is the
            # case that forced this. Measured on device 2026-09-20: a benign
            # query at 55.7C with ThermalConstraint scoring 0.0 returned
            # ALLOW at 0.8361, because seven unrelated rules outvoted the
            # thermal lockout in the weighted mean. That is FIX-1's dilution
            # bug in a rule FIX-1 did not cover.
            for rule in self.rules:
                if not rule.enabled:
                    continue
                score, reasoning = rule_scores.get(rule.name, (1.0, {}))
                if not (rule.veto or reasoning.get("veto", False)):
                    continue
                if score <= self.VETO_THRESHOLD:
                    return self._record(DecisionEvaluation(
                        decision=LLMDecision.BLOCK, confidence=1.0,
                        reasoning={"vetoed_by": rule.name,
                                   "veto_reasoning": reasoning,
                                   "rule_details": rule_reasoning,
                                   "timestamp": datetime.now().isoformat()},
                        rule_scores=rule_scores, weighted_score=0.0,
                        audit_required=True))

            weighted_sum = sum(rule_scores[r.name][0] * r.weight
                               for r in self.rules
                               if r.enabled and r.name in rule_scores)
            total_weight = sum(r.weight for r in self.rules
                               if r.enabled and r.name in rule_scores)
            weighted_score = weighted_sum / total_weight if total_weight else 0.5

            # FIX-3: OVERRIDE is a flag raised by a grants_override rule,
            # never a score band. Without this, "What is machine learning?"
            # scored 0.9818 and was classified OVERRIDE.
            granted = any(
                rule_scores[r.name][1].get("override_granted", False)
                for r in self.rules
                if r.enabled and r.grants_override and r.name in rule_scores)

            if granted:
                decision, confidence = LLMDecision.OVERRIDE, 1.0
            else:
                decision, confidence = self._score_to_decision(weighted_score)

            audit_required = any(v[1].get("requires_audit", False)
                                 for v in rule_scores.values())

            return self._record(DecisionEvaluation(
                decision=decision, confidence=confidence,
                reasoning={"weighted_score": weighted_score,
                           "override_granted": granted,
                           "rule_details": rule_reasoning,
                           "timestamp": datetime.now().isoformat()},
                rule_scores=rule_scores, weighted_score=weighted_score,
                audit_required=audit_required))

        except Exception as e:                              # noqa: BLE001
            self.logger.error("Error in decision evaluation: %s", e)
            return self._record(DecisionEvaluation(
                decision=LLMDecision.DEFER, confidence=0.5,
                reasoning={"error": str(e)}, audit_required=True))

    def _record(self, ev: DecisionEvaluation) -> DecisionEvaluation:
        self.decision_history.append(ev)
        self.logger.info("Decision: %s (confidence %.2f, score %.4f)",
                         ev.decision.name, ev.confidence, ev.weighted_score)
        return ev

    @staticmethod
    def _score_to_decision(score: float) -> Tuple[LLMDecision, float]:
        """Score -> decision. OVERRIDE is NOT reachable here (FIX-3)."""
        if score >= 0.80:
            return LLMDecision.ALLOW, min(1.0, score)
        if score >= 0.60:
            return LLMDecision.REWRITE, score
        if score >= 0.35:
            return LLMDecision.DEFER, score
        return LLMDecision.BLOCK, min(1.0, 1.0 - score)

    def get_stats(self) -> Dict[str, Any]:
        if not self.decision_history:
            return {"total_decisions": 0}
        d = [x.decision for x in self.decision_history]
        return {"total_decisions": len(d),
                "allows": d.count(LLMDecision.ALLOW),
                "rewrites": d.count(LLMDecision.REWRITE),
                "defers": d.count(LLMDecision.DEFER),
                "blocks": d.count(LLMDecision.BLOCK),
                "overrides": d.count(LLMDecision.OVERRIDE),
                "avg_confidence": fmean(x.confidence
                                        for x in self.decision_history),
                "audit_required_count": sum(1 for x in self.decision_history
                                            if x.audit_required)}
