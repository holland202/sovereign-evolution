# LEDGER

This repository serves two roles. It is an instrument — it contains working components with their own tests — and it is the ledger that records experiments across the instrument repositories. Those roles are not independent. Evidence recorded here about this repository's own components is self-reported and carries the weaker status that implies. Evidence recorded here about other repositories is a reference to work that lives and is tested elsewhere.

## How to read this directory

- `CLAIMS.md` — the claim ledger. Only the listed statuses are used. Most claims start as `NOT TESTED`.
- `INSTRUMENTS.md` — pointers to the instrument repositories by revision. Source code is not copied here.
- `PROTOCOL.md` — what admission of an experiment requires.
- `experiments/` — human-readable experiment records.
- `manifests/` — machine-readable twins of the experiment records.

A claim moves to `SUPPORTED` only when an experiment record names the revision, the seeds, the environment and the verdict that supports it. A claim moves to `REPRODUCED` only when a party other than the author has run it and recorded the result.

This layer establishes an evidence-accounting structure. It does not establish recursive self-improvement or any capability claim.
