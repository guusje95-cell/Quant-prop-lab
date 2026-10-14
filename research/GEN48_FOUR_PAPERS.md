# Gen48: four user-supplied papers (pre-registered)

- **Protocol:** `config/gen48_four_papers_protocol.json`, written before any run.
- **Code:** `src/qpl/lab/strategies_papers.py` and `src/qpl/lab/futures_curve.py`.
- **Script:** `scripts/gen48_four_papers.py`.
- **Results:** `results/gen48_four_papers.csv`.
- **Settings:** paper defaults throughout; nothing was tuned. Every run is listed. Sharpe is net of the stated cost.

## A. Time-series momentum + realized semivariance (Liu, Lu, Li & Wang 2023, J. Empirical Finance)

**Paper:** 31 Chinese commodity futures with 5-min data, 2008–2018. The best variant (TTSM-S2) reports Sharpe 1.78, against 1.37 for plain momentum.

**Our test:** 13 CFDs (4 indices, gold, silver, Brent, 6 FX), hourly data, 2013–2023, at 2 bp per side.

| Variant | Sharpe | CAGR | Max DD | Sharpe <2018-07 | Sharpe ≥2018-07 |
|---|---|---|---|---|---|
| TSM (no filter) | −1.01 | −16.9% | −85% | −1.15 | −0.93 |
| TTSM-S1 | −1.05 | −13.0% | −75% | −0.89 | −1.19 |
| **TTSM-S2 (paper best)** | **−0.85** | −9.1% | −62% | −0.54 | −1.10 |
| Crypto OKX perps, TSM, 7.5 bp | 0.73 | 4.8% | −10% | 0.98 | 0.55 |
| Crypto OKX perps, TTSM-S2 | 0.27 | 1.3% | −10% | 0.32 | 0.23 |

- Before costs, the filter does improve plain momentum on the CFDs: Sharpe −0.25 → +0.05. That is the paper's claim.
- But 20-day momentum on these markets earned nothing in 2013–2023.
- Daily rebalancing turns the book over about 500× a year, so costs dominate.
- On crypto, the filter hurts.

**Verdict: REJECTED.**

## B. Volatility-managed portfolios (Moreira & Muir 2017, J. Finance)

**Rule:** position = (average past monthly variance) / (last month's variance), rebalanced monthly. Data is equity-index futures (pysystemtrade, roll-adjusted), at 1 bp per side.

| Index | Buy & hold Sharpe | Vol-managed Sharpe | Max DD (B&H → VM) |
|---|---|---|---|
| **S&P 500 1991–2024** | 0.49 | **0.63** | −63% → −50% |
| S&P 500, capped 1.5× | | 0.62 | −48% |
| NASDAQ | 0.35 | 0.54 | −85% → −89% |
| DOW | 0.48 | 0.63 | −54% → −39% |
| DAX | 0.21 | 0.27 | −75% → −69% |
| EURO STOXX (2014+) | 0.53 | 0.45 | |
| FTSE 100 | 0.30 | 0.25 | |
| NIKKEI (2011+) | 0.74 | 0.77 | |
| BTC 2018+ (7.5 bp) | 0.81 | 0.73 | |

**Verdict: PASSED.** It beats buy & hold on the S&P 500 and on 4 of the 6 other indices; it does not help BTC.

- It is a risk-timing overlay on a long position, not a stand-alone trading edge.
- The gain is +0.1 to +0.2 Sharpe. Absolute Sharpe stays around 0.6, which is too low for prop challenges by itself.
- The useful idea is "cut risk after volatile months". C* already does a 30-day version of this per asset.

## C. Long around the European open (Bondarenko & Muravyev 2021)

**Paper:** E-mini S&P 500 futures, 1998–2020. Long from 23:30 to 03:30 New York time gave Sharpe 1.67.

| Data | Cost (bp/side) | Sharpe | CAGR |
|---|---|---|---|
| **US500 CFD 15-min, 2013–2023** | **1.0** | **−0.18** | −1.0% |
| US500 | 0.3 (futures-like) | 0.58 | 2.6% |
| US500 | 2.0 | −1.26 | |
| US100 | 1.0 | −0.03 | |
| US30 | 1.0 | −0.25 | |
| DE40 | 1.0 | 0.03 | |
| Real ES futures, Jan–Apr 2026 (3 months only) | 0.3 | 0.38 | |

- **Before costs** the window still earns: about +4.4% a year on US500, and positive in 8 of 11 years. 2020 contributed +23%, so it carries a big share of that.
- **The problem is cost.** Trading in and out every night costs about 5% a year at 1 bp per side. At real-futures cost (0.3 bp), Sharpe is about 0.6.

**Verdict: REJECTED** on the primary test (1 bp). Weak but positive at futures cost. Prop-firm suitability is low: about 2.6% a year, and the trade happens at night.

## D. Commodity momentum along the futures curve (de Groot, Karstanje & Zhou 2014, J. Banking & Finance)

**Paper:** 24 commodities, up to 12 contracts per curve. Net Sharpe 0.75 (optimal-roll) against 0.54 (generic).

**Our test:** about 28 commodities, using the 2–3 contracts per curve that pysystemtrade stores, 2000–2024, at 8 bp per trade.

| Variant | Sharpe | CAGR | Max DD | 2000–2011 | 2012–2024 |
|---|---|---|---|---|---|
| Generic (nearest contract) | 0.32 | 2.0% | −34% | 0.51 | 0.13 |
| **Optimal-roll (paper)** | **0.37** | 2.3% | −31% | 0.56 | 0.19 |

- The curve choice helps, as the paper says: +0.05 Sharpe, and a smaller drawdown.
- But commodity momentum itself has decayed since 2012.

**Verdict: NOT PASSED.** The threshold was Sharpe ≥ 0.4.

## Summary

- **One paper passed:** Moreira & Muir. It is a real but modest improvement for long equity exposure. It is not a stand-alone prop strategy.
- **Nothing from this generation beats C\*** (crypto trend, Sharpe 1.69 over the same 2018–2026 era) for prop-firm use.
- **Trials:** 31 runs in this generation, added to the project's total of about 230.
