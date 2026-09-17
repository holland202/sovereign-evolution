"""Minimal schemas for the Evidence Engine v0.1.

Only the fields required to enforce the core invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Completeness(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class ExperimentStatus(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    VOID = "VOID"


class VerdictStatus(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    NOT_ADMISSIBLE = "NOT_ADMISSIBLE"
    VOID = "VOID"
    REPRODUCED = "REPRODUCED"


ALLOWED_TRANSITIONS = {
    ExperimentStatus.NOT_TESTED: {ExperimentStatus.REGISTERED},
    ExperimentStatus.REGISTERED: {ExperimentStatus.RUNNING},
    ExperimentStatus.RUNNING: {ExperimentStatus.COMPLETE, ExperimentStatus.INCOMPLETE},
    ExperimentStatus.INCOMPLETE: {ExperimentStatus.VOID},
    ExperimentStatus.COMPLETE: {ExperimentStatus.VOID},
}


@dataclass
class InstrumentRef:
    repository: str
    revision: str


@dataclass
class AcceptanceCriteria:
    relative_improvement: float = 0.03
    sign_wins: int = 6
    paired_sem_max: float = 0.01


@dataclass
class ExperimentManifest:
    experiment_id: str
    claim_id: str
    instrument: InstrumentRef
    status: ExperimentStatus
    seeds_test_block: str
    budget_work_units: int
    arms: List[str]
    primary_metrics: List[str]
    acceptance: AcceptanceCriteria
    termination_incomplete_on: List[str] = field(
        default_factory=lambda: ["SIGKILL", "TIMEOUT", "MISSING_ARM", "MISSING_PRIMARY_METRIC"]
    )
    selective_retry_allowed: bool = False
    new_experiment_id_required_on_rerun: bool = True

    def is_revision_pinned(self) -> bool:
        rev = (self.instrument.revision or "").strip()
        return len(rev) >= 7 and all(c in "0123456789abcdef" for c in rev.lower())


@dataclass
class EvidenceRecord:
    evidence_id: str
    experiment_id: str
    exit_code: Optional[int]
    signal: Optional[str]
    cause: str = "UNDETERMINED"
    completeness: Completeness = Completeness.INCOMPLETE
    completed_arms: List[str] = field(default_factory=list)
    missing_arms: List[str] = field(default_factory=list)
    usable_for: List[str] = field(default_factory=list)
    not_sufficient_for: List[str] = field(default_factory=list)
    artifact_path: Optional[str] = None
    artifact_sha256: Optional[str] = None

    def is_complete(self) -> bool:
        return self.completeness == Completeness.COMPLETE and not self.missing_arms


@dataclass
class VerdictRecord:
    experiment_id: str
    status: VerdictStatus
    supported: bool
    refuted: bool
    reproduced: bool
    admissible: bool
    reason: str
    machine_derived: bool = True
