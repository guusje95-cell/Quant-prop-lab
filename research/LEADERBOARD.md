# Strategy leaderboard (all tracks; net of modelled costs). Updated 2026-10-10.
Sharpe = daily net returns; futures √256 (trading days), Dukascopy/HTF pooled series annualised by empirical days/yr, crypto √365. "OOS" = periods after the rule was frozen; "contaminated" = period previously viewed.

| # | Strategy | Track | Market | OOS / later evidence (net Sharpe) | Stressed cost | Trades / obs | Main weakness | Status |
|---|---|---|---|---|---|---|---|---|
| – | gen39–42 (2026-10-13/14, new data: OKX 58 perps hourly, Deribit funding, Yahoo 38 markets daily to 2026, FRED FX): XS crypto reversal/momentum/trend, funding contrarian, hourly shock reversal; multi-asset CFD trend (FX/indices/metals/energy); index calendar effects (TOM, pre-holiday, half-month); VIX-term-structure / 200d timed index exposure | multi | crypto, FX, indices, commodities | all REJECTED: best XS crypto trend 0.78 TEST but −0.77 VAL; CFD trend TEST −0.33 (gross 0.11); TOM 0.34 TEST but −0.40 VAL; VIX timing no better than buy&hold (0.5) | – | – | edges either absent net of costs or not robust across periods/markets | REJECTED (18 trials) |
| – | gen43–45 (2026-10-14): breadth (E2+O3 on PIT top-20/30), BTC/ETH funding carry (Deribit 2019–26), crypto volatility-risk-premium (short 30d variance via DVOL) | crypto | – | breadth worse than top-10 (TEST 0.97–1.03 vs 1.30); carry very steady but only 3.1%/yr TEST, 62% positive months; short vol TEST Sharpe −0.55, worst month −56% | – | – | – | REJECTED (4 trials) |
| **★** | **C*: E2 10 majors + stablecoin-liquidity overlay (gen38)** | crypto | Bybit perps, own account | 2018–26 net **1.67**, CAGR **24.1%** @15% vol; 2024–26 1.19 / 16.0%; fresh 2.01; DSR(N=136) 0.99; E2 replicated on untouched alts (0.96); O3 replicated (p=0.03) | 2× cost+funding 1.47 (TEST 0.95); 1-day delay 1.59 (TEST 0.72) | daily | worst day −12% → not CFT-daily-loss compatible at this risk; 2025 flat | **USER TARGET MET (Sharpe>1.3, CAGR>15%)** — research/CSTAR_E2_MAJ10_O3.md |
| – | gen35 macro E2 (FX/oil/SPX) on MT5; gen36 overlays MVRV, flows, VIX, USD, SPX, hash, addresses | cross-asset | – | macro TEST −0.60; MT5 crypto swaps kill trend; only O3 significant | – | – | – | REJECTED (O3 → replicated in gen37) |
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


## Gen47 (2026-10-14): intraday momentum papers on US index CFDs, 2013–2023, 15-min bars
- **Gao et al. 2018 (half-hour momentum): REJECTED.** Sharpe −1.06 on US500 at 1 bp.
- **Zarattini et al. 2024 (noise-area breakout): NOT PASSED.**
  - Primary test: Sharpe 0.36 on US500 at 1 bp.
  - US100: 0.71 at 1 bp, 1.12 at 0.3 bp. Positive in both halves.
  - Futures-prop candidate only; it needs real ES/NQ data to confirm. See `research/GEN47_INTRADAY_MOMENTUM.md`.


## Gen48 (2026-10-14): four user-supplied papers
Details are in `research/GEN48_FOUR_PAPERS.md`.

- **Semivariance-tuned momentum: REJECTED.** Sharpe −0.85 on 13 CFDs; costs dominate.
- **Volatility-managed portfolios: PASSED.** S&P 500 Sharpe goes from 0.49 to 0.63, and it helps on 4 of the 6 other indices. It is an overlay, not a stand-alone edge.
- **European-open long: REJECTED** at 1 bp (Sharpe −0.18). At futures cost it reaches 0.58.
- **Curve momentum: NOT PASSED.** Sharpe 0.37 against 0.32 for the generic version; the effect has decayed since 2012.


## Gen49–51 (2026-10-14): two more papers, then a search for something better than C*
Details are in `research/GEN49_51_SEARCH.md`.

- **Bianchi et al. 2023 (curve slope):** the data is unsuitable (stale prices). Rejected.
- **Liu & Tse 2017 (overnight):** rejected; costs remove its +5.5% a year before costs.
- **Baltussen et al. 2021:** rejected.
- **Multi-strategy mixes and a C* + S&P regime filter:** do not beat C*.
- **"Catching Crypto Trends" (Zarattini et al. 2025):** Sharpe 1.44 on the same coins. An independent confirmation of the crypto trend edge.
- **Daily equity stop at −3% on C* in prop challenges:** pass rate up 6–7 points and no more daily-loss fails. The profit effect is uncertain on hourly data. Not passed.


## Gen52 (2026-10-14): prop optimisation
About 5,900 trials: DEV 2018–22 to choose, TEST 2023–26 and an hourly replay to judge. Details are in `research/GEN52_PROP_OPTIMISATION.md`.

- **CFT 1-Phase:** nothing beats plain C* (1.0 / 0.4) on the hourly replay. Keep it.
- **FTMO 2-Step:** C* without the stablecoin filter, vol 20, band 0.2, challenge 1.5×, funded 0.6×, daily stop at 90%, take-profit 4%.
  - Net on TEST: $15.5k vs $6.9k for plain C*. Net on the hourly replay: $12.3k vs $10.9k.
  - Chance of profit on hourly: 99%. This passes the rule, but the result is promising, not proven.


## Gen53 (2026-10-14): literature-based improvements
Details are in `research/GEN53_RESEARCH.md`.

- **NEW BEST: C\* + BTC leads.** Altcoins are held only while BTC's own C* signal is positive.
  - Sharpe 1.78 (TEST 1.63) vs 1.69 (1.50); MDD −13.1% vs −15.1%.
  - It also improves the bias-free point-in-time top-10/top-20 universes, and the CFT and FTMO prop results on hourly prices.
- **Survivorship check:** point-in-time universes give C* a Sharpe of 1.27–1.44, against 1.78 for the fixed majors on the same data. Plan with about 1.4–1.5.
- **Rebalance tranching:** small gain (+0.07 TEST); not passed.
- **AHL continuous signal and portfolio covariance vol-targeting:** rejected.

## Gen55 (2026-10-14): which prop firm, with each firm's own rules and costs
Details are in `research/GEN55_FIRMS.md`. Strategy: C\* + BTC leads on hourly prices 2022–26, 1 account, 24 months.

- **Most robust:** the cheap two-steps with a fee refund. BrightFunded Bright, FundedNext Stellar, FTMO and HyroTrader Two-Step each net about $12–12.6k for about $550 in fees.
- **Most per $100k account:** HyroTrader One-Step, $13.7k (baseline) to $17.0k (1.5×/0.6× + daily stop).
- **Avoid:** Breakout (swap + tight limits; 25–48% pass) and SizeProp Degen (2%/3% limits; 24–37% pass).
- **Months with income stay at 12–25% at every firm.** Firm choice does not solve consistency; extra uncorrelated strategies are still needed.

## Gen56 (2026-10-14): five crypto papers
Details are in `research/GEN56_FIVE_PAPERS.md`.

- **Rejected:**
  - Wen et al. intraday hour pairs: out of sample, about 0 before costs.
  - Chi et al. basis / momentum / basis-momentum: basis TEST Sharpe +0.71 before costs, −0.42 after 5 bp, because turnover is 2.5× per day.
  - Cross-sectional momentum on 58 perps: DEV +1, TEST below 0.
  - Funding-forecast trading.
- **Replicated, but not tradable:** funding rates are predictable (MSPE −7–9%, 61–62% of directions correct).
- **New cost found:** about 0.8% of equity per year per coin in funding if C\* is held as perps.
- **Re-tests on the Binance pack:** pre-registered in `config/gen57_protocol.json`, before the data arrived.

## Gen58 (2026-10-15): what portfolio quality do we need? (theory, synthetic series)
Script: `scripts/gen58_target_sharpe.py`. Results: `results/gen58_target_sharpe.csv`.

Synthetic, smooth (fat-tailed but not trend-skewed) daily returns at 15% vol, run through the real prop engine. Per $100k account over 2 years, challenge 1.0×, funded 0.6×, FTMO 2-Step:

| Sharpe | Pass | Net, 2 years | Net, unlucky 10% | Months with income |
|---|---|---|---|---|
| 1.0 | 58% | $9.7k | $0.7k | 33% |
| 1.5 | 70% | $15.3k | $4.4k | 45% |
| 2.0 | 79% | $21.6k | $9.7k | 57% |
| 2.5 | 86% | $28.3k | $15.7k | 67% |
| 3.0 | 90% | $35.2k | $22.5k | 75% |

C\* (realistic Sharpe about 1.4–1.5) gets only about 21% months with income, against about 45% for a smooth Sharpe-1.5 series: trend profits are lumpy. **Smoothness matters as much as Sharpe.**

## Gen57 (2026-10-15): Binance futures pack
Details are in `research/GEN57_BINANCE.md`.

- **C\* realistic on perps:** funding costs 3.1%/yr, Sharpe 1.55 in 2023+ (1.75 for 2020–26). No overlay passes. Rebalancing at 08:00 UTC costs about 0.07.
- **Rejected:** noise-area intraday trend, the evening window on BTC, long-short session windows, premium reversion, positioning contrarian signals, CTREND, Gao, Wen, opening taker flow.
- **Promising, not validated:**
  - Liquidation-cascade buy: 2023+ 1.29, all 20 coins positive, survives 2x costs. But 2022 was negative, and it loses on the same crash days as C\*.
  - Funding carry XS: 7d average, 2023+ about 0.7.
  - ETH evening window with maker fills: 2023+ 0.99.
- **Descriptive combination 2023+:** C\* + 3 add-ons gives Sharpe 1.98 and **73% positive months** (C\* alone: 44%). This is optimistic, so the next step is forward testing.
