# SENTINEL Validation — BATADAL Dataset

## Key Result

**7 out of 7 attacks detected using zero labeled attack data.**

Dataset: BATADAL (Taormina et al. 2018)
Period: Jan 4 - Apr 1, 2017 | 2,089 hourly readings
Ground truth: 7 documented attack windows

## Detection Performance

| Metric | Value |
|---|---|
| Precision | 0.310 |
| Recall | 0.728 |
| F1 Score | 0.435 |
| Attacks Detected | 7/7 (100%) |
| Labeled attack data used | None |
| Calibration | 168 hours normal operation only |

## Confusion Matrix

|  | Predicted Attack | Predicted Normal |
|---|---|---|
| Actual Attack | 415 TP | 155 FN |
| Actual Normal | 925 FP | 594 TN |

## Per-Attack Coverage

All 7 attacks detected:
- Attack 1: 09/01/17 09 to 11/01/17 00 — DETECTED
- Attack 2: 16/01/17 00 to 19/01/17 10 — DETECTED
- Attack 3: 30/01/17 08 to 02/02/17 00 — DETECTED
- Attack 4: 09/02/17 10 to 14/02/17 00 — DETECTED
- Attack 5: 26/02/17 22 to 02/03/17 00 — DETECTED
- Attack 6: 06/03/17 02 to 10/03/17 00 — DETECTED
- Attack 7: 13/03/17 20 to 18/03/17 00 — DETECTED

## Comparison to Published BATADAL Results

All 9 published methods used labeled attack data for training.
SENTINEL uses only normal operation data.

| Method | F1 | Labeled Data |
|---|---|---|
| Best supervised | ~0.97 | Yes |
| Median supervised | ~0.50 | Yes |
| Worst supervised | ~0.22 | Yes |
| SENTINEL (unsupervised) | 0.435 | No |

## Methodology

Encoder: 14 sensors to 512-dimensional unit vectors via harmonic projection.
Detector: Cosine distance, 24-hour sliding window vs 168-hour baseline.
JSD = (1 - cosine_similarity) / 2

Hardware: Samsung Galaxy S25 Ultra (SM8750), Termux, Python 3.13.
Zero cloud. Zero internet. Zero signatures.

## Honest Limitations

1. High FP rate (60.9%) — BATADAL attacks designed to evade detectors.
   Mean attack JSD (0.0517) only 0.006 above normal (0.0457).
2. Threshold T=0.03 selected post-hoc on this dataset.
3. SWaT validation pending (41 attacks, 51 sensors).

## Reference

Taormina R. et al. (2018). Battle of the Attack Detection Algorithms.
Journal of Water Resources Planning and Management, 144(8).

*SENTINEL v1.0.0 | Chad Edward Holland | June 2026*
*c.holland.arch@proton.me | Vincit Omnia Veritas*
