"""Minimal in-memory / file-backed registry for v0.1."""

from __future__ import annotations

from typing import Dict, Optional

from .schemas import EvidenceRecord, ExperimentManifest


class Registry:
    def __init__(self) -> None:
        self.experiments: Dict[str, ExperimentManifest] = {}
        self.evidence: Dict[str, EvidenceRecord] = {}
        self.consumed_seeds: set[str] = set()

    def register_experiment(self, manifest: ExperimentManifest) -> None:
        if not manifest.is_revision_pinned():
            raise ValueError("Cannot register experiment with unpinned instrument revision")
        if manifest.seeds_test_block in self.consumed_seeds:
            raise ValueError(f"Seed block already consumed: {manifest.seeds_test_block}")
        self.experiments[manifest.experiment_id] = manifest

    def add_evidence(self, evidence: EvidenceRecord) -> None:
        if evidence.experiment_id not in self.experiments:
            raise ValueError(f"Unknown experiment: {evidence.experiment_id}")
        self.evidence[evidence.evidence_id] = evidence

    def mark_seed_consumed(self, block_id: str) -> None:
        self.consumed_seeds.add(block_id)

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentManifest]:
        return self.experiments.get(experiment_id)

    def get_evidence_for(self, experiment_id: str) -> list[EvidenceRecord]:
        return [e for e in self.evidence.values() if e.experiment_id == experiment_id]
