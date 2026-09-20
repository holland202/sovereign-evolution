Sovereign Evolution

Edge-native AI governance and evidence accounting, running locally on consumer hardware.

Sovereign Evolution is a research prototype for making AI systems observable, attributable, reproducible, and explicit about uncertainty.

It records what the system actually knows, what information is absent, which governance rules received usable inputs, which rules were operating without required evidence, which software components contributed to a decision, and whether the same recorded evidence produces a different verdict after a component changes.

No cloud dependency. No required external API. No silent substitution for missing evidence.

«Vincit Omnia Veritas — but only when checked.»

---

The Problem

An AI system can produce a confident-looking result while operating with incomplete information, hidden defaults, stale state, or changed software.

A successful execution is therefore not the same thing as a verified result.

Sovereign Evolution treats those conditions as part of the experiment.

The system makes the evidence conditions surrounding a decision inspectable:

INPUT
  ↓
CONTEXT
  ↓
EVIDENCE STATUS
  ↓
GOVERNANCE
  ↓
DECISION / VETO
  ↓
EXECUTION
  ↓
PROVENANCE
  ↓
REPLAY

The objective is not to make the system appear infallible.

The objective is to make failure visible, attributable, and testable.

---

Evidence Accounting

The runtime distinguishes different kinds of information rather than collapsing everything into a value.

State| Meaning
"MEASURED"| Obtained from an actual device or runtime source
"OPERATOR"| Explicitly supplied by the operator
"DERIVED"| Calculated from recorded runtime state
"ABSENT"| The requested information could not be obtained
"DEFAULTED"| A rule evaluated without the required supplied input
"NEVER WIRED"| A defined rule has no active data source in the runtime

This distinction matters.

For example:

thermal_temp       MEASURED    37.4°C
thermal_mode       MEASURED    UNRESTRICTED
battery_percent    MEASURED    44%
network_available  ABSENT      no probe implemented
llm_available      MEASURED    local server reachable
recent_blocks      DERIVED     0

The runtime can therefore report not only the decision, but the evidence conditions under which the decision was made.

Implemented code is not automatically an operational capability.

A rule that exists but has no reachable data source is recorded as such.

---

Governance Runtime

The current runtime executes locally on a Samsung Galaxy S25 Ultra using the Snapdragon 8 Elite platform.

The working execution path communicates with the local language model through "llama-server" over loopback HTTP.

The runtime currently supports:

- device thermal measurements;
- battery measurements;
- local model availability detection;
- operator input;
- derived runtime state;
- governance-rule completeness;
- rule-level scoring;
- veto attribution;
- component provenance;
- persistent decision logging;
- historical replay.

The runtime deliberately avoids turning unavailable information into fabricated measurements.

If a sensor cannot be read, the system records the absence.

If the local model cannot be reached, the system records the failure.

If a governance rule has no connected data source, the system reports that condition.

---

Evidence Engine

Sovereign Evolution includes an Evidence Engine for testing whether governance and verification mechanisms actually behave as claimed.

The Evidence Engine is not intended to certify a system merely because its code executes.

Its evaluation model is adversarial:

CLAIM
  ↓
IMPLEMENTATION
  ↓
TEST
  ↓
ADVERSARIAL TEST
  ↓
OBSERVATION
  ↓
VERDICT

The repository includes tests for both accepting and rejecting behavior, including cases where a governance mechanism can otherwise appear operational while lacking a reachable accepting or enforcing path.

A passing test establishes only the property that the test actually targets.

---

Provenance

Every runtime decision can carry provenance for the software components involved in producing it.

This provides a concrete answer to:

«Which implementation produced this verdict?»

A decision can therefore be associated with:

decision
+
recorded evidence
+
evidence status
+
rule attribution
+
component provenance

Component hashes make implementation changes visible instead of relying on undocumented version differences.

---

Replay and Verifier Drift

Historical decisions can be replayed against current components.

The basic question is:

«Given the same recorded inputs, does the current implementation produce the same verdict?»

If the answer changes, the replay identifies the disagreement and reports component changes associated with the historical decision.

This creates an experimental mechanism for measuring:

- verdict drift;
- implementation sensitivity;
- verifier expiration;
- reproducibility across component revisions.

Replay does not establish which verdict is correct.

It measures whether the decision procedure remained stable under the recorded evidence.

---

The D3 Question

One research thread in Sovereign Evolution examines verifier expiration.

A verifier can itself become stale as the system, environment, assumptions, or implementation changes.

The D3 experiment therefore treats the verifier as an object of measurement rather than an unquestioned authority.

The central question is:

«How much does the validity of a verification procedure degrade as the system it evaluates changes?»

The repository records this work in the research ledger rather than treating the existence of the experiment as proof of a general result.

---

Research Instruments

Sovereign Evolution acts as an evidence-accounting and research-operating layer for several independent instruments.

Eunoia

A manifold-based coherence experiment using residual distance as an operational measure of projection error.

The repository distinguishes repeated exposure from evidence of general semantic understanding.

Sovereign Titans

A governance-gated manifold-memory experiment examining persistent state formation under surprise and governance constraints.

Sentinel

An infrastructure anomaly-detection instrument based on distributional drift rather than fixed attack signatures.

Validation includes synthetic testing and BATADAL replay. Live ICS/SCADA operational effectiveness has not been established.

Sovereign Anima

A machine-identity research scaffold based on a per-machine manifold and separate live/background learning paths.

It is not presented as a validated capability.

IGAR

A causal-inference instrument implementing d-separation and the backdoor criterion, with explicit verdict gates intended to prevent unsupported causal conclusions.

Conformal Prediction

A distribution-free prediction-interval component with empirical coverage testing.

These instruments are independent research components.

Their presence in the same repository does not constitute a validated end-to-end AI system.

---

Research Ledger

The "LEDGER/" directory records claims, experiments, instrument revisions, protocols, environments, observations, and verdicts.

The intended evidence chain is:

CLAIM
  ↓
EXPERIMENT
  ↓
INSTRUMENT REVISION
  ↓
ENVIRONMENT / SEED
  ↓
OBSERVED RESULT
  ↓
VERDICT

The ledger is designed to preserve negative and incomplete evidence.

A failed experiment is not deleted because it produces an inconvenient result.

An incomplete experiment is not promoted to a successful one.

A demonstration is not automatically treated as validation.

---

Verification Vocabulary

Sovereign Evolution uses explicit evidence states:

Status| Meaning
"IMPLEMENTED"| Prototype code or tests exist
"EXPERIMENTAL"| Measurements have been obtained
"VERIFIED"| A test targeting the specific claim passed
"REPRODUCED"| An independent party reproduced the result
"REFUTED / UNVERIFIED"| Evidence contradicts or fails to establish the claim
"NOT TESTED"| The relevant question has not yet been evaluated

The distinctions are deliberate:

Implemented ≠ verified

Verified ≠ independently reproduced

Measured ≠ correct

Deterministic ≠ true

Passing a test ≠ proving a broader capability

---

Current Demonstration

The device runtime has demonstrated:

- explicit handling of unavailable measurements;
- measured thermal state and battery state;
- local model availability detection;
- evidence-completeness accounting;
- governance-rule attribution;
- intent-based veto behavior;
- local model execution;
- persistent decision logging;
- component provenance;
- replay of historical decisions.

For example, a destructive request can be intercepted by the active "DangerousIntent" rule before model generation, while benign requests can pass through to the local model.

These demonstrations establish runtime behavior.

They do not establish universal safety, universal correctness, or generalization beyond the tested environment.

---

What Has Not Been Established

Sovereign Evolution does not currently establish:

- recursive self-improvement;
- artificial general intelligence;
- machine consciousness;
- general semantic understanding;
- universal AI safety;
- production readiness for critical infrastructure;
- live ICS/SCADA operational effectiveness;
- cryptographic security against a determined adversary;
- multi-device generalization;
- independent third-party reproduction of all reported results.

These are not omissions from the record.

They are explicit boundaries on what the current evidence supports.

---

Architecture

                    ┌─────────────────────┐
                    │    Operator Input   │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Context Assembly  │
                    │                     │
                    │ measured / absent   │
                    │ operator / derived  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Evidence Engine   │
                    │                     │
                    │ rules / gates /     │
                    │ completeness        │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │      Decision       │
                    │    / Veto           │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │    Local LLM        │
                    │   / Execution       │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Evidence Ledger     │
                    │                     │
                    │ inputs              │
                    │ verdict             │
                    │ provenance          │
                    │ completeness        │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │       Replay        │
                    │                     │
                    │ drift / stability   │
                    └─────────────────────┘

See ""docs/ARCHITECTURE.md"" (docs/ARCHITECTURE.md) for implementation details.

---

Running the Runtime

Self-test

python3 sovereign_runtime.py --selftest

Runs the runtime's governance and evidence-accounting tests without requiring the language model.

Device probe

python3 sovereign_runtime.py --probe

Reports current measurements, unavailable inputs, evidence completeness, and component provenance.

Interactive runtime

python3 sovereign_runtime.py

Runs the local governance runtime and, when the local model is available, sends permitted requests to the on-device model.

Replay

python3 sovereign_runtime.py --replay decisions.jsonl

Replays historical decisions against the current components and reports verdict differences.

Test suite

python3 -m pytest

See ""STATUS.md"" (STATUS.md) before interpreting individual tests as evidence for broader research claims.

---

Research Direction

Current evaluation is focused on questions that can be experimentally falsified:

1. Does changing one governance component change historical verdicts?
2. How much verdict drift occurs after component revisions?
3. Do rules respond to the variables they are intended to govern?
4. What happens when required evidence is absent?
5. Can missing evidence be distinguished from a measured negative result?
6. Can historical decisions be reproduced across runtime versions?
7. Which failures originate in the detector, policy, context, verifier, or execution environment?
8. How does verifier validity change as the system evolves?

The purpose is not to manufacture successful demonstrations.

It is to determine where the system works, where it fails, and what the evidence actually supports.

---

Scope

Sovereign Evolution is a research prototype and evidence-accounting layer.

It is not presented as a production security product, a validated critical-infrastructure defense system, or evidence of artificial general intelligence, machine consciousness, or recursive self-improvement.

Claims are maintained separately from implementations, experiments, and results so that unsupported conclusions remain visible.

---

Repository Documentation

- ""STATUS.md"" (STATUS.md) — current verification and evidence status
- ""PROVENANCE.md"" (PROVENANCE.md) — project identity, lineage, and research-status definitions
- ""LEDGER/"" (LEDGER/) — claims, experiments, and evidence records
- ""docs/ARCHITECTURE.md"" (docs/ARCHITECTURE.md) — system architecture
- ""CITATION.cff"" (CITATION.cff) — citation information
- ""LICENSE"" (LICENSE) — MIT License

---

License

MIT.

---

Built locally. Tested explicitly. Failures retained.

Vincit Omnia Veritas — but only when checked.
