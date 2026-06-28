# SENTINEL Detection Results — Water Treatment Profile

Demo run: 150 ticks, 3 attacks injected, 3 detected.

| Tick | JSD Score | Attack Type | Reading |
|------|-----------|-------------|---------|
| T=046 | 0.3750 | pH tampering (Oldsmar-style) | pH→9.8, Cl→0.05 |
| T=081 | 0.3765 | Valve closure (flow shutoff) | Flow→3.2 MGD, Press→83 PSI |
| T=111 | 0.6671 | Catastrophic — CRITICAL | Flow→0.7, Press→250+ PSI |

Normal operation JSD: 0.01–0.09
Attack detection threshold: 0.10
Detection latency: 1–3 ticks (~0.1–0.24 seconds)

Zero false positives during 80-tick normal baseline.
Zero cloud. Zero signatures. Zero internet.
