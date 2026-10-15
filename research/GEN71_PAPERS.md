# Gen71: uploaded papers 6-9 (last crypto batch)

Pre-registered in `config/gen71_protocol.json` before any number was computed. Script: `scripts/gen71_papers.py`; results in `results/gen71_papers.csv`; daily series in `results/cache_gen71_daily.parquet`. Trials added: 7. Same pass rule as Gen70 (v4 on the daily recipe: Sharpe 1.94).

| Idea | DEV | TEST | HOLD | 2023+ | corr C* | corr v4 | v4 + it | Verdict |
|---|---|---|---|---|---|---|---|---|
| Z1 Zarattini Donchian combo, long-only (PRIMARY) | 0.66 | 1.65 | 0.01 | 1.06 | 0.66 | 0.39 | 1.76 | rejected |
| Z2 combo, long-short | 0.64 | 0.59 | -0.25 | 0.17 | 0.35 | 0.21 | 1.71 | info only |
| Z3 combo, BTC only | -0.19 | 1.43 | -0.30 | 0.80 | 0.58 | 0.28 | 1.70 | info only |
| Z1 replacing C* in v4 | | | | | | | 1.77 | rejected (C* itself: TEST 2.29, HOLD 0.56) |
| G1 Guo BTC-lead quintile, 5m (PRIMARY) | -54.8 | -77.3 | -78.4 | -77.8 | 0.13 | 0.11 | — | rejected |
| G2 adaptive LASSO, 5m | -25.8 | -17.9 | -16.4 | -17.2 | 0.00 | 0.05 | — | info only |
| G3 BTC-lead, 1h | -5.9 | -10.1 | -13.0 | -11.3 | 0.16 | 0.06 | — | info only |
| S1 Borri et al. CMOM (PRIMARY) | 0.77 | 0.14 | 0.15 | 0.14 | 0.07 | 0.04 | 1.96 | rejected (TEST < 0.8) |

## Notes

**Zarattini et al. (Donchian ensemble).** The exact rule is a solid long-only trend follower, but it is the same bet as C* (correlation 0.66). It is weaker than C* in every split, and it does nothing in 2025-26 (HOLD 0.01). As a replacement for C* it lowers v4 from 1.94 to 1.77. Our C* (trend + BTC leads, the earlier-validated version) stays.

**Guo et al. (cross-crypto lead-lag).** The effect is real before costs: the 5-minute BTC-lead quintile book earns about 1% per day gross (gross Sharpe ~5, 2020-26). It is not tradable. Rebalancing every 5 minutes at 4 bp per unit of turnover costs far more than the edge, and at 1 hour the edge is gone before costs.
- Part of the gross edge is likely non-synchronous last-trade prices, not money a taker can capture.
- A high-frequency strategy like this is also outside what prop firms allow.
- This matches our earlier lead-lag rejections; C* already uses BTC leads at the daily horizon where it survives costs.

**Borri et al. (survey, CMOM).** Two-week momentum works in 2020-22 and then fades (TEST 0.14). On v4 it adds only +0.02 Sharpe, and it fails the TEST gate. CSIZE and CVALUE are not testable: there are no market caps or on-chain address data, and the size premium sits in coins outside the perp universe.

**Gornall, Rinaldi & Xiao (perpetual futures and basis risk).** Not applicable. The strategy is spot-versus-futures cash-and-carry; crypto prop firms offer perps only, so there is no spot leg. Its message (funding keeps perps close to spot, so perp basis trades have small, fast-reverting drawdowns) is consistent with our premium-carry sleeve working.

## Paper batch summary (Gen70 + Gen71, 8 papers)
- One new sleeve passed: the **Weiss expiry reversal** (Gen70 W1), a v5 candidate at half weight.
- Everything else was either the same bet we already hold (trend vs C*, funding vs premium carry), small-cap only (CTREND, CSIZE), or untradable after costs (minute lead-lag).
