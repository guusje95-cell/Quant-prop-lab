# Strategy leaderboard (all tracks; net of modelled costs). Updated 2026-10-10.
Sharpe = daily net returns; futures √256 (trading days), Dukascopy/HTF pooled series annualised by empirical days/yr, crypto √365. "OOS" = periods after the rule was frozen; "contaminated" = period previously viewed.

| # | Strategy | Track | Market | OOS / later evidence (net Sharpe) | Stressed cost | Trades / obs | Main weakness | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | F9 / F7 trend + carry (V6) | B | 155 futures, 1975–2024 | F7: VAL 0.63 · TEST 0.96 · HOLDOUT 0.70 (single looks) | 3× cost VAL 0.16 (0.28 buffered) | daily, 50 yrs | cost-sensitive; decayed (~1.5 → ~0.8 post-2010); needs ~$1M | ELIGIBLE (F7) / PROMISING (F9) |
| 2 | HTFD_A2_BO_PW: weekly-level breakout, daily bars | A | BTC | DEV 0.88 · VAL 0.75 · TEST 0.86 (MTM 0.89/0.72/1.21) | 2× cost TEST 0.77 | 121/50/111 trades | TEST BTC path previously observed; corr 0.36–0.55 with CT1; 11-coin transfer 0.62 but ex-DOGE 0.36 / ex-2021 0.28 | PROMISING_BUT_UNVALIDATED |
| 2a | Gen26 crypto zoo finalists: MULTI short-breakout 7/2 LO · MULTI RSI-mom 14 LO · BTC TSMOM30 LS/LO | crypto | top-10 alts / BTC | TEST 1.07 / 0.92 / 0.90 / 0.73 (VAL 1.15/0.80/1.70/2.00) | 2× TEST 0.78/0.71/0.78/0.52; 3× 0.61/0.65/0.69/0.46 | daily | DSR (N=104) 0.17/0.22/0.12/0.36 < 0.90; PBO BTC 0.13, MULTI 0.33; CFT 2-Phase no risk level with daily-breach ≤10% (cons.); TSMOM30 2024–26 0.09/0.46 | PROMISING – failed selection-bias + prop gates |
| 3 | CT1 BTC trend ensemble (V4) | crypto | BTC | OOS 0.57 · holdout 0.34; 21 perps −0.02 | 21 bp 0.19 | daily | conditional long beta; decayed | PROMISING_BUT_UNVALIDATED |
| 4 | HTFD_A1_SR1_PM: monthly-level sweep & reclaim, daily | A | 13 CFD/FX | DEV only: 0.34 (MTM 0.55) | – | 415 trades | only 46% of instruments positive | REJECTED (near miss) |
| 5 | HTFD_A3_SR3_PM: monthly failed breakout, daily | A | 13 CFD/FX | DEV only: 0.44 (MTM 0.40) | – | 256 | below 0.5 gate | REJECTED (near miss) |
| – | HTF 1-hour sweep / failed-breakout / breakout (12 primaries) | A | 13 CFD/FX + BTC | DEV: −2.23 … +0.27 net; A1_SR1_PD gross +1.17 | – | 57–8,401 | gross edge +0.06R < costs ~0.1R/trade | REJECTED |
| – | Daily breakout PW/PM on CFD/FX | A | 13 CFD/FX | DEV −0.30 / +0.11 | – | 1,985 / 518 | no continuation on CFD/FX | REJECTED |
| – | C21 rolling-hedge pairs stat-arb (6 pairs) | C | Dukascopy D1 | DEV −0.35 net (gross 0.13); all 4 neighbours < 0 | 2× −0.51 | 218 trades | no reversion edge after costs | REJECTED |
| – | All V6 regime/ML/XS/crypto-on-chain families | B/C | – | see v6/V6_RESULTS.md | – | – | – | REJECTED |

## Portfolio check (descriptive; all periods previously viewed; weekly, trailing-vol equal risk), 2015-01 → 2024-03
| | F9 | BTC_BO_PW | CT1 | F9+BO | F9+CT1 | F9+BO+CT1 |
|---|---|---|---|---|---|---|
| Sharpe | 0.73 | 0.91 | 1.31 | 1.16 | 1.40 | 1.46 |
| Max DD | −12.6% | −11.8% | −8.6% | −8.7% | −7.5% | −7.7% |

Correlations: F9–BO 0.02, F9–CT1 0.08, BO–CT1 0.37. The crypto sleeves' Sharpe is dominated by 2015–21. Forward, CT1 is ~0.4 (post-2021).
