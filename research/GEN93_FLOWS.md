# Gen93: forced-flow family on BTC/ETH CFDs (2026-10-18)

- **Protocol:** `config/gen93_protocol.json`, registered before any number. 3 trials.
- **Scripts:** `scripts/gen93_flows.py` and `scripts/gen93_check.py`.
- **Baseline:** the Gen90 CFD book, Sharpe 1.797.

| Test | Signal days | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Corr C* | Book after | Rule verdict |
|---|---|---|---|---|---|---|---|
| **M1 stablecoin mint spike** (USDT+USDC +0.5% in a day, 2-day lag -> long BTC/ETH 3 days) | 296 | 1.01 | 1.79 | 0.33 | 0.34 | **1.875** | **passes** |
| M2 perp deep-discount bounce (premium below its 5th percentile) | 292 | 0.63 | -0.47 | -0.09 | 0.05 | 1.27 | rejected |
| M3 funding flush (3 negative fundings and a 3-day drop -> long 2 days) | 115 | 0.28 | 1.15 | 1.26 | 0.02 | 1.75 | rejected: passes alone, lowers the book |

## M1 robustness (descriptive)

| Check | DEV | TEST | HOLD |
|---|---|---|---|
| base | 1.01 | 1.79 | 0.37 |
| threshold 0.3% / 0.75% / 1.0% | 0.97 / 1.08 / 0.92 | 1.95 / 2.15 / 1.03 | **-0.33 / -0.41 / -0.53** |
| hold 2 / 5 days | 0.77 / 0.94 | 1.72 / 1.52 | 0.53 / 0.76 |
| lag 3 / 4 days | 1.21 / 0.81 | 1.85 / 0.95 | 0.43 / 0.56 |
| BTC only / ETH only | 0.69 / 1.16 | 1.89 / 1.48 | 0.32 / 0.36 |
| 2x spread | 0.97 | 1.71 | 0.28 |
| reference: always long BTC/ETH | 0.91 | 1.42 | -0.33 |

**Random entry days, same count (300 draws):**
- Mean Sharpe 0.41, 95th percentile 0.93; M1 is 0.99 (p = 0.04).
- So the timing adds something over plain long exposure.

**Signals are front-loaded:**
- 2020: 98 days; 2021: 90; 2022: 17; 2023: 21; 2024: 39; 2025: 29; 2026: 2.
- The stablecoin data ends 2026-05.

## Verdict: passed the rule, but NOT added to the main book

- **HOLD flips negative at every nearby threshold.** The 2025-26 result therefore rests on the exact 0.5% setting and about 30 signal days.
- **It is a long-BTC/ETH timing trade,** correlated 0.34 with C\*, which already uses stablecoin growth as a filter.
- **Decision:** this is the same standard Gen69 applied to vol targeting. A pass that only holds at the exact setting is not treated as robust.
- **M1 goes to the paper ledger / watchlist.**
- **Book figures:** the main CFD book stays at **1.80**; for reference, with M1 it would be 1.88.
