# Strategy leaderboard (all tracks; net of modelled costs). Updated 2026-10-10.
Sharpe = daily net returns; futures √256 (trading days), Dukascopy/HTF pooled series annualised by empirical days/yr, crypto √365. "OOS" = periods after the rule was frozen; "contaminated" = period previously viewed.

| # | Strategy | Track | Market | OOS / later evidence (net Sharpe) | Stressed cost | Trades / obs | Main weakness | Status |
|---|---|---|---|---|---|---|---|---|
| **00** | **Two-speed CFT 1-Phase pipeline (gen34): challenge = E2 10 majors v=15%, funded = E2 BTC+ETH v=6%** | crypto / CFT | Bybit perps | same frozen E2 signal | fee 1.5%: +6.1%; 2× cost: +5.8%; delay: +1.9% (2023–24 starts, 24-mo net) | daily | alt wicks in challenge (priced in as re-buys); 2023–26 seen | **BETTER (pre-registered)**: median 4.0 mo to funded (vs 8.2), 40% funded ≤90 d, 24-mo net +7.6% acct (P>0 98%) on 2023–24 starts; bootstrap +7.7% (P>0 83%) |
| – | gen32/33 signal changes (range-vol, 9-family ensemble, breadth, 4h BTC, LS, ETH/BTC rel-trend) | crypto | BTC/ETH | none beat E2 in every period | – | – | – | REJECTED |
| **0** | **E2 LIQUID2: BTC+ETH daily trend+breakout ensemble, long-only (gen31)** | crypto / CFT | BTC, ETH (Bybit perps) | 2018–26 net 1.36 · 2023–26 1.24 · fresh 2026-05→10 1.68; DSR(N=112) 0.93 | 2×cost+funding 0.95; 1-day delay 1.05 | daily, ~8–10 turnover/yr | slow (~7–8%/yr at 1-Phase risk; 2025–26 +2%/yr); 2023–26 previously seen | **APPLICABLE (CFT 1-Phase, v=6%)**: pass 78% (2023–24 starts) / 62% bootstrap, daily fail 0–1%, EV +3.7% acct/attempt — see research/CFT_E2_LIQUID2_PLAYBOOK.md |
| 0b | E2 on 10 majors (gen28/30) | crypto / CFT | 10 Binance majors | 2023–26 net 1.41, stress 1.15 | – | daily | alt crash wicks (2024-03-05, 2025-10-10: −55..−85%) → daily-loss breaches 16–18%, EV<0 | FAILED prop gate |
| 1 | F9 / F7 trend + carry (V6) | B | 155 futures, 1975–2024 | F7: VAL 0.63 · TEST 0.96 · HOLDOUT 0.70 (single looks) | 3× cost VAL 0.16 (0.28 buffered) | daily, 50 yrs | cost-sensitive; decayed (~1.5 → ~0.8 post-2010); needs ~$1M | ELIGIBLE (F7) / PROMISING (F9) |
| 2 | HTFD_A2_BO_PW: weekly-level breakout, daily bars | A | BTC | DEV 0.88 · VAL 0.75 · TEST 0.86 (MTM 0.89/0.72/1.21) | 2× cost TEST 0.77 | 121/50/111 trades | TEST BTC path previously observed; corr 0.36–0.55 with CT1; 11-coin transfer 0.62 but ex-DOGE 0.36 / ex-2021 0.28 | PROMISING_BUT_UNVALIDATED |
| 2a | Gen26 crypto zoo finalists: MULTI short-breakout 7/2 LO · MULTI RSI-mom 14 LO · BTC TSMOM30 LS/LO | crypto | top-10 alts / BTC | TEST 1.07 / 0.92 / 0.90 / 0.73 (VAL 1.15/0.80/1.70/2.00) | 2× TEST 0.78/0.71/0.78/0.52; 3× 0.61/0.65/0.69/0.46 | daily | DSR (N=104) 0.17/0.22/0.12/0.36 < 0.90; PBO BTC 0.13, MULTI 0.33; CFT 2-Phase no risk level with daily-breach ≤10% (cons.); TSMOM30 2024–26 0.09/0.46 | PROMISING – failed selection-bias + prop gates |
| 2b | Gen27 replication of the 4 frozen finalists on untouched coins ranked 11–30 (2018–2026-05, 15 bp) | crypto | 20 alts | net 0.77 / 0.74 / 0.61 / 0.62; 2018–21 ≈1.2–1.3, 2022–26 0.32 / 0.18 / 0.03 / −0.05 | 2× 0.47 / 0.63 / 0.39 / 0.48 | daily | Holm p 0.10 > 0.05; edge concentrated pre-2022 | REPLICATION FAILED (direction confirmed, not significant) |
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
