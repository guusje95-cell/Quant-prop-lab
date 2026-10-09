# V6 Results: leaderboard and candidate sheets

All numbers are read from `results/v6_*.json`. **Clean** means the period was untouched when the rule was frozen.
**Contaminated** means the period had already been viewed (single looks, or any later re-use). Every hypothesis tested in
the project, including all failures, is in `v6/V6_HYPOTHESIS_REGISTRY.csv`:
* 56 hypotheses: 41 REJECTED, 4 EXPLORATORY, 6 PROMISING_BUT_UNVALIDATED, 5 ELIGIBLE_FOR_INDEPENDENT_VALIDATION.
* Unique variants are counted per protocol.

## 1. Leaderboard (net of costs; Sharpe on daily P&L, √256 for futures, √365 for crypto)

| Rank | Candidate | Status | Clean evidence | Contaminated evidence | Main risk |
|---|---|---|---|---|---|
| 1 | **F7_COMBO** (trend ×3 + carry, signal average), futures | ELIGIBLE | DISC 1.51 · VAL 0.63 · TEST 0.96 (1 look) · HOLDOUT 0.70 (1 look) | – | costs (3×: VAL 0.16); leverage 7–11× notional |
| 2 | **F2_EWMAC**, futures | ELIGIBLE | 1.43 · 0.61 · 0.90 · 0.70 | – | same; lowest-turnover trend |
| 3 | **F1_TSMOM**, futures | ELIGIBLE | 1.35 · 0.52 · 0.90 · 0.61 | – | costs |
| 4 | **F3_CARRY**, futures | ELIGIBLE | 1.15 · 0.80 · 0.82 · 0.44 | – | holdout weakest; DISC max DD −47% |
| 5 | **F0_CT1_TRANSFER** (frozen crypto idea on futures) | ELIGIBLE | 1.16 · 0.34 · 0.60 · 0.51 | – | highest turnover (435×/yr in TEST) |
| 6 | **F9_SLEEVE_RP** (equal risk trend/carry sleeves, buffered) | PROMISING | DISC 1.60 | VAL 0.90 (construction chosen on 1995–2013) · TEST 1.21 · HOLDOUT 0.73 | construction post-hoc; skew −1.9 in HOLDOUT |
| 7 | **CT1** BTC trend ensemble | PROMISING | TRAIN 1.51 · VAL 1.28 · OOS 0.57 · BTC holdout 0.34 | ETH 0.93 ✓, 21 perps 2025–26 −0.02 ✗ | decayed; it is conditional long beta (short leg ≈ 0) |
| 8 | G14 buffering (implementation layer) | PROMISING | F7 at 3× costs: VAL 0.16 → 0.28 (b = 0.05) | TEST/HOLDOUT ↑ | – |
| – | Long-only risk parity futures (benchmark) | benchmark | DISC 0.55 · VAL 0.95 | TEST 0.22 · HOLDOUT 0.01 | – |

### Rejected or exploratory in V6 (all kept)

| Candidate | Result |
|---|---|
| F4 XS momentum | DISC 0.48; gross 1.05 lost to 5.7%/yr costs |
| F5 XS value | 0.19 |
| F6 skew | −0.15 |
| H15a HMM regime weights | 1.37 vs baseline 1.34; random p95 1.39 |
| H15b BOCPD de-risking | 1.37 vs 1.34; random p95 1.38 |
| H15c factor momentum | 1.39 vs 1.34; random p95 1.41 |
| H15d ridge | 0.99 vs F7 1.09 |
| H15d LightGBM | 1.14 vs F7 1.09 (P ≤ F7 0.38) |
| H16a crypto XS momentum | 0.25 |
| H16b crypto weekly reversal | −1.27 |
| H16c on-chain MVRV value | −0.29 |
| H16d network growth | −0.26 |
| H16e BTC MVRV timing | residual vs buy-and-hold −0.37 |

Earlier V4 and v1/v3 rejections are in the registry.

## 2. Candidate sheet: F7_COMBO (futures trend + carry). Equivalent sheets for F0–F3 are in `results/v6_futures_gen13.json` and `v6_futures_audit.json`.

| Metric | DISCOVERY 1975–2004 | VALIDATION 2005–13 | TEST 2014–19 | HOLDOUT 2020–24Q1 |
|---|---|---|---|---|
| Net Sharpe (95% block-bootstrap CI) | 1.51 (1.16, 1.87) | 0.63 (0.07, 1.29) | 0.96 (0.12, 1.76) | 0.70 (−0.22, 1.56) |
| Gross Sharpe | 1.85 | 0.86 | 1.29 | 0.94 |
| Ann. return / vol | 15.4% / 10.2% | 6.3% / 10.1% | 10.5% / 11.0% | 7.4% / 10.7% |
| Max DD (additive) | −13% | −18% | −20% | −21% |
| Costs p.a. / turnover ×/yr | 3.4% / 95 | 2.4% / 185 | 3.7% / 297 | 2.6% / 238 |
| Mean gross notional | 3.7× | 6.8× | 11.4× | 6.8× |
| Beta to long-only RP / residual Sharpe | −0.02 / 1.51 | 0.19 / ~0.6 | −0.16 / 1.00 | −0.15 / ~0.7 |
| Net Sharpe at 2× / 3× costs | 1.18 / 0.85 | 0.39 / 0.16 | 0.62 / 0.29 | 0.46 / 0.21 |
| With buffer b = 0.05 (1× / 3×) | 1.57 / 1.05 | 0.66 / 0.28 | 1.00 / 0.47 | 0.73 / 0.33 |

* **Year by year** (`results/v6_futures_audit.json` A2): 2008 +33%, 2009 −0%, 2011–13 ≈ −6…+1%, 2014 +44%, 2022 +21%, 2023 −6%. This matches the known trend-industry pattern.
* **Concentration:** 54–64% of instruments contribute positively; the top 5 are about 20–23% of P&L. Bonds were the largest contributor 2014–19; ags/energy/bonds in 2020–24.
* **Parameter sensitivity:**
  * Every trend lookback (21–252 days) and every EWMAC speed is positive in DISCOVERY.
  * CSCV PBO over the 26-config grid is 0.017.
  * A random half of the universe still gives TEST 0.50–0.98.
  * Execution lag of 1–5 days changes Sharpe by < 0.2.
* **Selection risk:** 42 futures configurations tried in total. DSR 1985–2024 = 0.79; post-2014 alone = 0.37.
* **Data limits:**
  * The instrument list is a practitioner's current list (mild survivorship).
  * Universe filters use full-sample cost/vol (non-performance).
  * Bad-tick repair uses t+1.
  * Hourly stitching after 2013 was verified against Dukascopy (weekly corr 0.89–0.99).
* **Failure modes:**
  * Trend droughts like 2011–13 and 2016–18.
  * Cost blow-out (3× costs ≈ break-even in VALIDATION).
  * Sharp reversal days (HOLDOUT skew −0.7 to −1.9).
  * Leverage and margin needs of 7–11× notional.
  * At least $1M of capital needed for a faithful implementation.
* **Evidence still needed:** a prospective record, with costs measured from real fills. Even so, MinTRL says SR 0.5 needs about 10 years to be significant on its own. Decisions must therefore lean on the 50-year cross-market record.

## 3. Candidate sheet: F9_SLEEVE_RP (frozen for prospective paper; `config/f9_spec.json`)

| Metric | DISCOVERY (clean) | VALIDATION (construction-contaminated) | TEST (contaminated) | HOLDOUT (contaminated) |
|---|---|---|---|---|
| Net Sharpe (CI) | 1.60 (1.21, 1.97) | 0.90 (0.32, 1.47) | 1.21 (0.42, 1.98) | 0.73 (−0.13, 1.62) |
| Gross Sharpe | 1.80 | 1.06 | 1.45 | 0.91 |
| Ann. ret / vol / max DD | 16.4% / 10.3% / −16% | 9.2% / 10.1% / −16% | 12.8% / 10.5% / −17% | 7.7% / 10.6% / −17% |
| Skew / CVaR5 (daily) | 0.02 / −1.4% | −0.40 / −1.5% | −0.57 / −1.6% | −1.91 / −1.7% |
| Costs p.a. / turnover | 2.1% / 60 | 1.6% / 121 | 2.5% / 190 | 1.9% / 160 |
| Residual vs long-only RP (beta) | 1.69 (−0.13) | 0.78 (0.14) | 1.22 (−0.04) | 0.73 (−0.03) |
| 2× / 3× costs | 1.39 / 1.19 | 0.75 / 0.59 | 0.98 / 0.74 | 0.55 / 0.38 |

* **Sensitivity** (trend mix 0.3–0.7 × buffer 0–0.2): DISC 1.47–1.67, VAL 0.75–0.94, TEST 1.07–1.25, HOLDOUT 0.63–0.77. A flat region.
* **Worst drawdowns:**
  * −45% in 1971–72, a warm-up artefact with fewer than 16 instruments and the vol target still calibrating.
  * Otherwise −17% (2016–17), −17% (2022-10 → 2023-09) and −16% (1994).
  * 63% of months are positive. Worst months: 2018-02 −10%, 2023-07 −9%, 2021-11 −9%, 2023-03 −9%.
* **Implementation:** integer contracts track continuous weights at ≥ $1M (correlation 0.94). At $250k only about 13 instruments are held at 5.5% vol, and $100k is not viable.
* **Monitoring expectation, deliberately conservative:** SR 0.5, vol 10%.

## 4. Crypto CT1 in the portfolio
* Correlation with the futures sleeves is 0.09, and about 0 in the futures book's worst weeks. CT1 is crisis-convex, like trend.
* At 1/3 risk it added +0.46 Sharpe in 2015–24, driven by CT1's 2015–21 period. Using its post-2021 Sharpe of 0.4, the expected gain is about +0.1.
* Recommended role: a small diversifying sleeve, long/flat preferred (Entry 2).

## 5. What is *not* established
* No candidate has prospective evidence.
* No recent window is individually significant.
* No intraday, microstructure, option or macro-event edge was testable with reachable data.
* No prop-firm route exists for multi-day futures trend/carry: intraday-flat rules make it incompatible.
* No crypto prop rule is verified (official sites are unreachable).
