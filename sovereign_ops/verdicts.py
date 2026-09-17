"""Verdict authorization logic for Evidence Engine v0.1.

Core invariants enforced here:

I1  INCOMPLETE \u2192 SUPPORTED        FORBIDDEN
I2  INCOMPLETE \u2192 REFUTED          FORBIDDEN
I3  SIGKILL \u2192 OOM                 FORBIDDEN without independent evidence
I4  partial arm \u2192 complete verdict FORBIDDEN
I7  unpinned instrument revision \u2192 admissible  FORBIDDEN
I8  verdict text \u2192 determines status       FORBIDDEN
I9  machine verdict \u2192 deterministic        REQUIRED
"""

from __future__ import annotations

from .schemas import (
    Completeness,
    EvidenceRecord,
    ExperimentManifest,
    ExperimentStatus,
    VerdictRecord,
    VerdictStatus,
)


def authorize_verdict(
    manifest: ExperimentManifest,
    evidence: EvidenceRecord,
) -> VerdictRecord:
    """Return a machine-derived verdict. Never promotes incomplete evidence."""

    reasons: list[str] = []

    if not manifest.is_revision_pinned():
        reasons.append("Instrument revision is not pinned to a git SHA.")
        return _denied(manifest.experiment_id, reasons, VerdictStatus.VOID)

    if evidence.completeness != Completeness.COMPLETE:
        reasons.append("Evidence completeness is INCOMPLETE.")
    if evidence.missing_arms:
        reasons.append(f"Missing registered arms: {evidence.missing_arms}.")
    if not evidence.is_complete():
        reasons.append("Required evidence set incomplete.")
        reasons.append("No capability claim may be promoted.")
        return _denied(manifest.experiment_id, reasons, VerdictStatus.VOID)

    reasons.append("Evidence set complete; numerical criterion evaluation not implemented in v0.1.")
    return VerdictRecord(
        experiment_id=manifest.experiment_id,
        status=VerdictStatus.NOT_ADMISSIBLE,
        supported=False,
        refuted=False,
        reproduced=False,
        admissible=False,
        reason="; ".join(reasons),
        machine_derived=True,
    )


def _denied(experiment_id: str, reasons: list[str], status: VerdictStatus) -> VerdictRecord:
    return VerdictRecord(
        experiment_id=experiment_id,
        status=status,
        supported=False,
        refuted=False,
        reproduced=False,
        admissible=False,
        reason="; ".join(reasons),
        machine_derived=True,
    )


def sigkill_cause(exit_code: int | None, signal: str | None) -> str:
    """I3: 137/SIGKILL never auto-becomes OOM."""
    if exit_code == 137 or (signal or "").upper() == "SIGKILL":
        return "UNDETERMINED"
    return "UNDETERMINED"
