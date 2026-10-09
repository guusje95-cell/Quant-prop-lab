# V6 Statistical Audit: methods, assumptions, and where each was or wasn't used

## Validation design
| Method | Where | Assumptions / why chosen | Limitations |
|---|---|---|---|
| Chronological DISCOVERY → VALIDATION → TEST → HOLDOUT, gated in code | futures gen13, crypto gen16, V4 crypto | Protocols committed to git **before** the first return was computed (bb24d93, 5373c4f, d8b1625), so the timestamps are verifiable. Later stages run only if the earlier gate passes. | Published-effect knowledge (trend/carry history) cannot be removed. TEST/HOLDOUT are confirmation, not discovery. |
| Expanding annual walk-forward with refit, 22-day purge | gen15 regime & ML | The target window (t+2..t+21) overlaps, so training rows whose target ends after the refit date are purged. HMM states use the **forward filter** only (smoothing would leak). | Daily rebalanced overlays ignore reweighting cost (stated). |
| Random-control baselines (block-shuffled weights, 63-day blocks, 200 draws) | gen15 overlays, V4 C9, v3 filters | Keeps the overlay's exposure distribution; breaks its timing. Tests whether *timing* adds value. | Block length is a choice; 63 days ≈ one quarter. |
| Neighbour/variant gates (≥ 70% or 2/3 positive) | every family | Guards against a narrow-parameter artefact. | Coarse grids. |
| Stationary block bootstrap (Politis–Romano), block 20 days | Sharpe CIs, differences | Autocorrelated, heteroskedastic daily P&L. | Assumes stationarity within a period. |
| Newey–West t (10 lags) + Holm across family primaries | gen13 | HAC for overlapping positions; Holm controls FWER across 5–7 families. | Per-window tests have low power: 4–6 years of SR ~0.7 is rarely significant on its own. |
| CSCV PBO (16 blocks, 12,870 splits) | futures gen13 grid (26 configs, 1985–2013) | Probability that the in-sample winner ranks below the out-of-sample median. | Only measures selection *within* the grid, not across all project research. |
| PSR / DSR (Bailey & López de Prado) | futures survivors, CT1 | Skew/kurtosis-adjusted; DSR deflates by the number of trials (42 futures configs) and the variance of SR across them. | The trial count is per data domain. Pooling the v1/v3 intraday and crypto trials would deflate further, but those were different selection problems. |
| MinTRL | futures survivors | Years of data needed to reject SR ≤ 0 at 95%. | Informs what a prospective track can and cannot show. |
| Cost stress 2×/3×/5×, lag 1–5 days, random half-universes | futures audit | Implementation fragility. | Spread estimates are the repository's own. |
| Cross-source data validation | futures vs Dukascopy | Independent provenance check on 9 instruments. | Different contract specs; weekly returns used. |

## Contamination register (what has been looked at, and how many times)
| Data / period | Looks | Consequence |
|---|---|---|
| Futures panel DISCOVERY 1975–2004 | many (exploration allowed) | – |
| Futures VALIDATION 2005–13 | gen13 gated looks for 4 families; gen14 implementation decisions; gen15 walk-forward 1995–2013 | F9's construction was chosen after B0 > F7 here, so F9 VALIDATION is not clean |
| Futures TEST 2014–19 | 1 look each for F0–F3 and F7 (gen13) | Every later use is labelled contaminated |
| Futures HOLDOUT 2020–24Q1 | 1 look each for F0–F3 and F7 (gen13) | Same |
| BTC 2024-01..2026-10 | CT1 single look (V4); later descriptive | USED |
| Binance perps 2025-08..2026-09 | CT1 transfer (V4), C7 carry | USED |
| Coin Metrics 2017–2020 (TRAIN) | 5 gen16 hypotheses, all rejected at TRAIN | VALIDATION and TEST still unused for new XS crypto ideas |

## Known statistical weaknesses that remain
1. **Power.** Recent windows can't confirm SR ~0.5–0.8 on their own. The case rests on long-sample, cross-market consistency.
2. **Knowledge contamination.** Trend and carry are among the best-known anomalies, and the protocol can't erase that prior.
3. **Universe construction.** The futures list is current-practitioner curated. Crypto (Coin Metrics) is curated with some dead assets.
4. **Cost model.** Spread estimates are not measured fills. 3× costs makes VALIDATION trend roughly break-even. Buffering mitigates this.
5. **Annualisation.** √256 for futures trading days and √365 for crypto calendar days. Cross-asset comparisons use weekly sums.
6. **Drawdowns** are additive (sum of daily returns), not compounded. Compounded drawdowns at 10% vol differ by under 1 percentage point.

## Bugs found in V6 (all fixed, regression-tested or re-run, superseded numbers kept)
| ID | Defect | Impact |
|---|---|---|
| V6-B1 | G14c integer-contract band coded as max(0.5, 10%) instead of 0.5 + 10% | rounding churn |
| V6-B1b | Exchange-holiday NaN contract notional zeroed targets, forcing round trips | G14c first showed Sharpe < 0 even at $5M. Main engine checked and unaffected. Fixed in `futures_panel.contract_notional` |
| V6-D1 | gen14/15 hypotheses had ledger decisions but no SQLite rows | registry bookkeeping only |
| Data | decimal-shift bad ticks in pysystemtrade data | spike filter; documented t+1 repair |
