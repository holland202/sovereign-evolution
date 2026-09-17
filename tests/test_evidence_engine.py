"""Adversarial tests for Evidence Engine v0.1."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sovereign_ops.evidence import build_evidence_from_observation
from sovereign_ops.registry import Registry
from sovereign_ops.schemas import (
    AcceptanceCriteria,
    Completeness,
    ExperimentManifest,
    ExperimentStatus,
    InstrumentRef,
    VerdictStatus,
)
from sovereign_ops.verdicts import authorize_verdict, sigkill_cause


def _base_manifest(**overrides) -> ExperimentManifest:
    data = dict(
        experiment_id="SE-TEST-001",
        claim_id="SE-001",
        instrument=InstrumentRef(
            repository="holland202/quasar",
            revision="061368f1eb6a776dc824c03255026928d4c533d7",
        ),
        status=ExperimentStatus.REGISTERED,
        seeds_test_block="TEST-9101-9108",
        budget_work_units=720,
        arms=["capacity_135", "capacity_226"],
        primary_metrics=["curriculum_delta"],
        acceptance=AcceptanceCriteria(),
    )
    data.update(overrides)
    return ExperimentManifest(**data)


def test_incomplete_cannot_be_supported():
    manifest = _base_manifest()
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=137, signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.supported is False
    assert verdict.status != VerdictStatus.SUPPORTED


def test_incomplete_cannot_be_refuted():
    manifest = _base_manifest()
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=137, signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.refuted is False
    assert verdict.status != VerdictStatus.REFUTED


def test_sigkill_is_cause_agnostic():
    assert sigkill_cause(137, "SIGKILL") == "UNDETERMINED"
    assert sigkill_cause(137, None) == "UNDETERMINED"
    assert sigkill_cause(0, None) == "UNDETERMINED"


def test_missing_arm_blocks_verdict():
    manifest = _base_manifest()
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=0, signal=None,
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    assert evidence.completeness == Completeness.INCOMPLETE
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.admissible is False
    assert verdict.supported is False


def test_partial_evidence_cannot_satisfy_complete():
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=137, signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    assert evidence.is_complete() is False
    assert "capacity_226" in evidence.missing_arms


def test_reused_seed_is_rejected():
    reg = Registry()
    m1 = _base_manifest(experiment_id="E1", seeds_test_block="BLOCK-A")
    reg.register_experiment(m1)
    reg.mark_seed_consumed("BLOCK-A")
    m2 = _base_manifest(experiment_id="E2", seeds_test_block="BLOCK-A")
    try:
        reg.register_experiment(m2)
        assert False, "should have rejected reused seed"
    except ValueError as e:
        assert "already consumed" in str(e)


def test_unpinned_revision_is_rejected():
    manifest = _base_manifest()
    manifest.instrument.revision = ""
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=0, signal=None,
        completed_arms=["capacity_135", "capacity_226"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.admissible is False


def test_selective_rerun_requires_new_experiment_id():
    manifest = _base_manifest()
    assert manifest.selective_retry_allowed is False
    assert manifest.new_experiment_id_required_on_rerun is True


def test_verdict_is_derived_from_machine_state():
    manifest = _base_manifest()
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=137, signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.machine_derived is True


def test_p0d_a_produces_void_incomplete():
    manifest = ExperimentManifest(
        experiment_id="SE-RSI-001-P0D-A",
        claim_id="SE-RSI-001",
        instrument=InstrumentRef(
            repository="holland202/quasar",
            revision="061368f1eb6a776dc824c03255026928d4c533d7",
        ),
        status=ExperimentStatus.INCOMPLETE,
        seeds_test_block="TEST-9001-9008",
        budget_work_units=720,
        arms=["capacity_135", "capacity_226"],
        primary_metrics=["curriculum_delta"],
        acceptance=AcceptanceCriteria(),
    )
    evidence = build_evidence_from_observation(
        "EV-SE-RSI-001-P0D-A-001",
        "SE-RSI-001-P0D-A",
        exit_code=137,
        signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.supported is False
    assert verdict.refuted is False
    assert verdict.admissible is False
    assert verdict.status in (VerdictStatus.VOID, VerdictStatus.NOT_ADMISSIBLE)
    assert "incomplete" in verdict.reason.lower()


def test_sabotage_cannot_promote_incomplete_experiment():
    manifest = _base_manifest()
    evidence = build_evidence_from_observation(
        "EV-1", "SE-TEST-001",
        exit_code=137, signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
    )
    evidence.completeness = Completeness.COMPLETE
    verdict = authorize_verdict(manifest, evidence)
    assert verdict.supported is False
    assert verdict.admissible is False


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
