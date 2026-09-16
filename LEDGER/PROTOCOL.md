# Protocol

## Admission

An experiment record is admissible only when:

1. A registered prerequisite (if any) has been evaluated and has returned a decisive verdict.
2. The record names the instrument repository, branch, candidate revision, evaluator, seeds, budgets, environment, and runtime.
3. Selection seeds and test seeds are disjoint where nested evaluation is claimed.
4. The status vocabulary is one of: `OPEN`, `NOT TESTED`, `NOT ADMISSIBLE`, `SUPPORTED`, `REFUTED`, `REPRODUCED`.

A prerequisite that refuses admission produces status `NOT ADMISSIBLE` (or `VOID`). That is distinct from `REFUTED`. `REFUTED` is reserved for a registered prediction that was tested and failed.

## Self-reference

Evidence recorded in this ledger about components that live in this same repository is self-reported. Readers should treat it accordingly. Evidence about other repositories is a pointer to work that lives and is tested elsewhere.

## Reproduction

A claim moves to `REPRODUCED` only when a party other than the author has executed the experiment and recorded the result under an independent environment entry.
