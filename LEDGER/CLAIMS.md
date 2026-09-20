# Claims

| ID | Claim | Evidence | Status |
|----|-------|----------|--------|
| SE-001 | A bounded recursive self-improvement experiment can be specified with a registered prerequisite that can refuse to admit it | `SE-RSI-001` | SUPPORTED |
| SE-002 | An evolved curriculum policy outperforms fixed curricula on held-out loss | `SE-RSI-001` | NOT TESTED |
| SE-003 | A modified system improves its own capacity to discover further improvements | — | NOT TESTED |
| SE-004 | A recursive sequence Q0 → Q1 → Q2 has been demonstrated | — | NOT TESTED |
| ENGINE-001 | `sovereign_ops` v0.1 derives an admissible verdict from a complete evidence set | `probe_engine_accepts.py` @ `d43820c` | REFUTED |

A claim moves to SUPPORTED only when an experiment record in `experiments/` names the revision, the seeds, the environment and the verdict that supports it. A claim moves to REPRODUCED only when a party other than the author has run it and recorded the result. No claim in this ledger is currently REPRODUCED.

Statuses in this table are entered against the documentary standard above. They are not derived by `sovereign_ops/`; see `ENGINE-001` for that component's measured capability. `ENGINE-001` is scoped to v0.1: the engine's own reason string records that numerical criterion evaluation is not implemented at that version, and `probe_engine_accepts.py` measured that a complete evidence set with a pinned revision still returns `NOT_ADMISSIBLE`.
