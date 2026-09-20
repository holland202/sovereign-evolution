Sovereign Evolution

Edge-native AI governance and evidence accounting, running locally on consumer hardware.

Sovereign Evolution is a research prototype for making AI decisions observable, attributable, replayable, and explicit about uncertainty.

It records what the system actually knows, what it does not know, which governance rules received usable inputs, which rules were operating on defaults or were not wired, which software components contributed to a decision, and whether the same recorded evidence produces a different verdict after a component changes.

No cloud. No required external API. No silent substitution for missing evidence.

«Vincit Omnia Veritas — but only when checked.»

---

What Problem Does It Address?

An AI system can produce a confident-looking decision even when important information is unavailable, when a rule silently falls back to a default, or when the software making the decision has changed.

A successful execution is therefore not the same thing as a verified result.

Sovereign Evolution treats those conditions as part of the experiment rather than hiding them.

The runtime distinguishes between:

- MEASURED — obtained from an actual device or runtime source.
- OPERATOR — explicitly supplied by the operator.
- DERIVED — calculated from recorded runtime state.
- ABSENT — the requested information could not be obtained.
- DEFAULTED — a rule had to operate without the required supplied input.
- NEVER WIRED — a defined rule has no active data source in the current runtime.

This turns incomplete context from an invisible implementation detail into a measurable property of each decision.

---

Core Principle

Sovereign Evolution does not ask:

«“Did the AI produce an answer?”»

It asks:

«“What evidence was available when the system made its decision, what rules actually operated on that evidence, and can the decision be reproduced and audited?”»

Every decision can carry:

INPUTS
  ↓
MEASUREMENT STATUS
  ↓
GOVERNANCE RULES
  ↓
DECISION / VETO
  ↓
MODEL EXECUTION
  ↓
PROVENANCE
  ↓
REPLAY

The objective is not to make the system appear infallible.

The objective is to make failure visible and testable.

---

Current Runtime

The current device runtime executes locally on a Samsung Galaxy S25 Ultra using the Snapdragon 8 Elite platform.

The working runtime communicates with the local language model through "llama-server" over loopback HTTP rather than requiring the Python "llama_cpp" binding.

The runtime can currently measure and record:

- device thermal state and temperature;
- battery state;
- local model availability;
- operator input;
- derived runtime state such as recent governance blocks;
- governance-rule completeness;
- rule-level scores and veto attribution;
- component hashes;
- generated-response status;
- decision history for replay.

Missing information is recorded as missing rather than replaced with an invented measurement.

---

Governance and Evidence Accounting

A decision is not treated as a single opaque "ALLOW" or "BLOCK".

The runtime records the context under which the verdict occurred.

For example:

thermal_temp       MEASURED   37.4°C
thermal_mode       MEASURED   UNRESTRICTED
battery_percent    MEASURED   44%
network_available  ABSENT     no probe implemented
llm_available      MEASURED   local server reachable
recent_blocks      DERIVED    0

The runtime can then report that some rules received supplied data while another rule operated without its required input.

Rules that are not connected to a data source are explicitly identified rather than represented as operational.

This distinction is central to the project:

implemented code is not automatically an operational capability.

---

Provenance

Each decision records hashes of the software components that contributed to it.

This provides a concrete answer to:

«“Which implementation produced this verdict?”»

The provenance layer is intended to make changes auditable rather than relying on memory or undocumented version differences.

A decision can therefore be associated with:

decision
+
recorded evidence
+
context completeness
+
rule attribution
+
component provenance

---

Replay and Verifier Drift

Historical decisions can be replayed against current components.

The basic question is:

«Given the same recorded inputs, does the current implementation produce the same verdict?»

If it does not, the system reports the disagreement and identifies component changes associated with the historical decision.

This provides an experimental mechanism for studying verdict drift and verifier expiration.

Replay does not prove that either verdict is correct.

It measures whether the decision procedure remained stable under the recorded evidence.

---

Local AI Components

Sovereign Evolution is also an integration and research-operating layer for several independent instruments and prototypes.

Eunoia

A manifold-based coherence experiment using residual distance as an operational measure of projection error.

The repository documents the important limitation: repeated exposure to the same phrase is not equivalent to demonstrating general semantic understanding.

Sovereign Titans

A governance-gated manifold-memory experiment in which high-surprise, insufficiently governed events can form persistent scars while governed inputs are prevented from doing so.

Sentinel

An infrastructure anomaly-detection instrument using distributional drift rather than fixed attack signatures.

Current validation includes synthetic simulation and BATADAL replay. It has not been validated against live ICS/SCADA telemetry.

Sovereign Anima

A machine-identity concept based on a per-machine manifold and separate live/background learning paths.

It remains a scaffold and is not presented as a validated capability.

IGAR

A causal-inference instrument implementing Pearl-style d-separation and the backdoor criterion, including explicit refusal when a valid adjustment set cannot be established.

Conformal Prediction

A distribution-free prediction-interval component with locally tested empirical coverage.

These instruments should not be interpreted as a single validated end-to-end capability merely because they coexist in this repository.

---

Research Ledger

The "LEDGER/" directory records claims, experiments, instrument revisions, protocols, and evidence.

The ledger deliberately separates:

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

The ledger is an evidence-accounting layer.

It is not itself proof of recursive self-improvement, general intelligence, autonomy, or any other capability claim.

A claim is not promoted merely because the implementation exists or because a demonstration produces a plausible output.

---

Verification Status

Sovereign Evolution distinguishes between:

Status| Meaning
"IMPLEMENTED"| Prototype code and tests exist
"EXPERIMENTAL"| Prototype measurements have been obtained
"VERIFIED"| A test targeting the specific claim has passed
"REPRODUCED"| An independent party has reproduced the result
"REFUTED / UNVERIFIED"| Evidence contradicts or does not establish the claim
"NOT TESTED"| The relevant question has not yet been evaluated

Implemented does not mean verified.

Verified does not mean independently reproduced.

Measured does not mean universally valid.

Deterministic does not mean correct.

A passing test does not establish a broader capability than the test actually targets.

The repository intentionally retains failures, limitations, incomplete experiments, and unverified components rather than removing them from the record.

See ""STATUS.md"" (STATUS.md) for the current verification ledger.

---

What Has Actually Been Demonstrated?

The current prototype has demonstrated, on-device:

- explicit handling of absent measurements;
- context-completeness accounting;
- attribution of a governance veto to the active intent rule;
- local model availability detection;
- local model generation through the runtime;
- component provenance attached to decisions;
- persistent decision logging;
- replay of historical decisions against current components.

The runtime has also demonstrated that a destructive request can be blocked before model generation while benign requests are allowed through to the local model.

These are runtime demonstrations, not claims of universal safety or correctness.

---

What Has Not Been Established?

The project does not currently establish:

- recursive self-improvement;
- artificial general intelligence;
- machine consciousness;
- general semantic understanding;
- production readiness for critical infrastructure;
- universal AI safety;
- cryptographic security against a determined adversary;
- independent third-party reproduction;
- multi-device generalization;
- live ICS/SCADA operational effectiveness.

Several component-level results remain limited to single-device experiments, internal data, synthetic environments, or public replay datasets.

Those limitations are part of the project's evidence record.

---

Architecture

At a high level:

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
                    │ Governance Engine   │
                    │                     │
                    │ rules / veto /      │
                    │ completeness        │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │      Decision       │
                    └──────────┬──────────┘
                               ↓
                 ┌───────────────────────────┐
                 │ Local LLM / Execution     │
                 └────────────┬──────────────┘
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
                    │ verdict stability   │
                    │ component drift     │
                    └─────────────────────┘

Detailed component architecture is documented in ""docs/ARCHITECTURE.md"" (docs/ARCHITECTURE.md).

---

Running the Prototype

Evidence-accounted runtime

python3 sovereign_runtime.py --selftest
python3 sovereign_runtime.py --probe
python3 sovereign_runtime.py

The self-test validates the runtime's evidence-accounting and governance mechanics without requiring the language model.

The probe reports current device measurements, missing inputs, rule completeness, and component provenance.

The interactive runtime executes governance decisions and, when the local model is available, passes permitted requests to the on-device model.

Replay

python3 sovereign_runtime.py --replay decisions.jsonl

Replay compares historical decisions with decisions produced by the current components.

Existing component tests

python3 -m pytest

See ""STATUS.md"" (STATUS.md) before interpreting test results as evidence for a broader claim.

---

Research Direction

The next stage is controlled evaluation of the governance and verification layer.

Important questions include:

1. Does changing a single governance component change historical verdicts?
2. How much verdict drift occurs under component revisions?
3. Do governance rules respond specifically to the variables they claim to govern?
4. What happens when required evidence is absent?
5. Can a rule distinguish missing evidence from a measured negative result?
6. Can historical decisions be reproduced across runtime versions?
7. Which failures are caused by the detector, the policy, the context, the verifier, or the execution environment?
8. How does verification degrade as components and assumptions change?

The purpose of these experiments is not to manufacture a successful demonstration.

It is to determine where the system works, where it fails, and what the evidence actually supports.

---

Scope

Sovereign Evolution is a research prototype and evidence-accounting layer.

It should not be interpreted as a production security product, a validated critical-infrastructure defense system, or evidence of general intelligence or recursive self-improvement.

Claims are maintained separately from implementations, experiments, and results so that unsupported conclusions remain visible.

---

License

MIT.

See ""LICENSE"" (LICENSE).

Provenance

See ""PROVENANCE.md"" (PROVENANCE.md) for repository identity, research-status definitions, experimental lineage, and explicit non-claims.

---

Built locally. Tested explicitly. Failures retained.

Vincit Omnia Veritas — but only when checked.
