# SE-RSI-001

```
Experiment ID:      SE-RSI-001
Title:              RSI-1 substrate qualification (P0)
Date:               2026-09-16
Instrument repo:    holland202/quasar
Branch:             rsi-meta-curriculum
Candidate revision: 061368f1eb6a776dc824c03255026928d4c533d7
Record commit:      894955b
Gate test commit:   fdde056
Lineage on main:    c3d6f73
Evaluator:          held-out Bures loss, make_holdout(seed=777, n=16), unmodified
Seed hash:          10c3814e9f7c178b
Selection seeds:    1001-1008  (reserved, never used)
Test seeds:         9001-9008  (used; disjoint from selection)
Budgets:            80 / 240 / 720 work units
Environment:        Python 3.14.6, NumPy 2.4.4, Android-16-aarch64
Device:             Samsung Galaxy S25 Ultra, Termux
Runtime:            2594.6 s
Verdict:            P0b = FALSE
Status:             NOT ADMISSIBLE (VOID)
R1:                 NOT TESTED
R2:                 NOT TESTED
Reproduction:       none recorded
```

## Results (verbatim)

```
 80 units   error -0.27% (1/8)   progress -0.05% (4/8)   SEM 0.0013 / 0.0024
240 units   error +0.20% (7/8)   progress +0.16% (5/8)   SEM 0.0007 / 0.0021
720 units   error -0.22% (2/8)   progress -0.27% (3/8)   SEM 0.0014 / 0.0020
uniform holdout loss: 0.23433 -> 0.21208 -> 0.18027
```

## Interpretation (limited to three points)

1. The bar was +3% relative with a 6-of-8 sign test. Every contrast fell short by an order of magnitude.

2. The anti-vacuity control passed at every budget — paired SEMs of 0.0007 to 0.0024 against a 0.01 resolution bar — so these are resolved nulls, not underpowered measurements. The instrument could have detected a 3% effect. There was not one.

3. The outer loop was never run, so R1 and R2 were never tested. This is `NOT ADMISSIBLE`, not a tested-and-failed prediction. The status vocabulary reserves `REFUTED` for the latter case; that word is not used for this record.

## Carry-forward (unresolved)

- An unexplained direction reversal in the `error` contrast between 240 and 720 units — an observation with no mechanism, sitting about 2-3 SEM from zero on effects 15x below the decision bar. **Not a finding.**
- `P0d`, unrun: raise model capacity to the quasar-v2 F16 regime (225 parameters, not 135) and re-test the precondition.

The gate was later self-tested in both verdict directions (`fdde056`, 10 checks, sabotage-proven). That is self-testing, not independent verification — the same author wrote the instrument and the test.
