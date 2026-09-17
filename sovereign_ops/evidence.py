"""Evidence helpers for Evidence Engine v0.1."""

from __future__ import annotations

from .schemas import Completeness, EvidenceRecord
from .verdicts import sigkill_cause


def build_evidence_from_observation(
    evidence_id: str,
    experiment_id: str,
    *,
    exit_code: int | None,
    signal: str | None,
    completed_arms: list[str],
    registered_arms: list[str],
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
) -> EvidenceRecord:
    """Construct an EvidenceRecord from observed execution facts only."""

    missing = [a for a in registered_arms if a not in completed_arms]
    complete = len(missing) == 0 and exit_code == 0

    cause = sigkill_cause(exit_code, signal)

    usable = []
    not_sufficient = []
    if exit_code is not None:
        usable.append("termination_observation")
    if not complete:
        not_sufficient.extend([
            "curriculum_verdict",
            "capacity_effect",
            "RSI_admission",
        ])

    return EvidenceRecord(
        evidence_id=evidence_id,
        experiment_id=experiment_id,
        exit_code=exit_code,
        signal=signal,
        cause=cause,
        completeness=Completeness.COMPLETE if complete else Completeness.INCOMPLETE,
        completed_arms=list(completed_arms),
        missing_arms=missing,
        usable_for=usable,
        not_sufficient_for=not_sufficient,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
    )
