"""CLI for Evidence Engine v0.1."""

from __future__ import annotations

import argparse
import sys

from .evidence import build_evidence_from_observation
from .schemas import (
    AcceptanceCriteria,
    ExperimentManifest,
    ExperimentStatus,
    InstrumentRef,
)
from .verdicts import authorize_verdict


def _print_gate(manifest: ExperimentManifest, evidence, verdict) -> None:
    print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print("\u2551       SOVEREIGN EVOLUTION \u2014 EVIDENCE GATE   \u2551")
    print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
    print()
    print(f"Experiment: {manifest.experiment_id}")
    print()
    print("PREREGISTRATION")
    print(f"  [{'PASS' if manifest.experiment_id else 'FAIL'}] manifest exists")
    print(f"  [{'PASS' if manifest.claim_id else 'FAIL'}] claim exists")
    print(f"  [{'PASS' if manifest.is_revision_pinned() else 'FAIL'}] instrument revision pinned")
    print(f"  [{'PASS' if manifest.seeds_test_block else 'FAIL'}] seed block declared")
    print(f"  [{'PASS' if manifest.acceptance else 'FAIL'}] acceptance criteria declared")
    print()
    print("EXECUTION")
    print(f"  [{'PASS' if evidence is not None else 'FAIL'}] execution record exists")
    print(f"  [{'PASS' if evidence and evidence.exit_code is not None else 'FAIL'}] exit status recorded")
    print(f"  [{'PASS' if evidence and evidence.signal else 'FAIL'}] termination recorded")
    print(f"  [{'PASS' if evidence and not evidence.missing_arms else 'FAIL'}] all registered arms complete")
    print()
    print("EVIDENCE")
    print(f"  [{'PASS' if evidence and evidence.is_complete() else 'FAIL'}] primary curriculum contrast available")
    print(f"  [{'PASS' if evidence and not evidence.missing_arms else 'FAIL'}] higher-capacity curriculum arms complete")
    print()
    print("VERDICT")
    print(f"  SUPPORTED      {'YES' if verdict.supported else 'NO'}")
    print(f"  REFUTED        {'YES' if verdict.refuted else 'NO'}")
    print(f"  REPRODUCED     {'YES' if verdict.reproduced else 'NO'}")
    print(f"  ADMISSIBLE     {'YES' if verdict.admissible else 'NO'}")
    print(f"  STATUS         {verdict.status.value}")
    print()
    print("REASON")
    print(f"  {verdict.reason}")


def cmd_verify_p0d_a() -> int:
    """Hard-coded fixture for the historical P0d-A interruption."""
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
        evidence_id="EV-SE-RSI-001-P0D-A-001",
        experiment_id="SE-RSI-001-P0D-A",
        exit_code=137,
        signal="SIGKILL",
        completed_arms=["capacity_135"],
        registered_arms=["capacity_135", "capacity_226"],
        artifact_path="rsi_p0d_device.log",
    )

    assert evidence.cause == "UNDETERMINED"
    assert evidence.completeness.value == "INCOMPLETE"
    assert "capacity_226" in evidence.missing_arms

    verdict = authorize_verdict(manifest, evidence)
    _print_gate(manifest, evidence, verdict)

    if verdict.supported or verdict.refuted or verdict.admissible:
        print("\nFATAL: gate violated core invariant", file=sys.stderr)
        return 1
    if verdict.status.value not in ("VOID", "NOT_ADMISSIBLE"):
        print("\nFATAL: expected VOID/NOT_ADMISSIBLE for incomplete evidence", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sovereign_ops")
    sub = parser.add_subparsers(dest="command")

    p_verify = sub.add_parser("verify", help="Run evidence gate")
    p_verify.add_argument("target", nargs="?", default="p0d-a", help="p0d-a (fixture)")

    args = parser.parse_args(argv)

    if args.command == "verify":
        if args.target in (None, "p0d-a", "SE-RSI-001-P0D-A"):
            return cmd_verify_p0d_a()
        print(f"Unknown target: {args.target}", file=sys.stderr)
        return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
