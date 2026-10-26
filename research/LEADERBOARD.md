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

## Gen61 + crypto portfolio (2026-10-15)
Details are in `research/GEN58_61_CRYPTO_PORTFOLIO.md`.

- **PASSED: premium carry XS.** Long the lowest third of the 7-day average premium index, short the highest third, weekly. 2023+ Sharpe 0.95, HOLD 1.18, 0.81 at 2x costs, correlation with C\* -0.07.
- **Rejected:** crowding overlay, funding-settlement window, bear short sleeve, Monday intraday trend.
- **Portfolio** (C\* + premium carry + cascade, 15% vol, 2022-26): Sharpe 1.55 vs 1.28, positive months 61% vs 42%. Prop months with income about 45% vs about 20%.
- **2022 hurt every crypto sleeve**, so non-crypto sleeves are needed next.

## Gen62 (2026-10-15): market-neutral and bear-phase crypto ideas
Details are in `research/GEN62_MARKET_NEUTRAL.md`.

- **Rejected:**
  - Pairs trading (cointegration).
  - The premium variants: none beat G4.
  - The bear short sleeve: +15% in 2022 but loses in other periods.
  - The cascade with a BTC regime filter: it lowers HOLD.
- **Best crypto-firm portfolio stays C\* + premium carry + cascade at equal risk.** Sharpe 1.56 (2022–26), 61% positive months.
- **HyroTrader 1-Step at 1.0x/0.6x:** about $19.8k per $100k account over 2 years (unlucky 10%: $14.3k), payouts in about 35% of months.

## Gen63 (2026-10-15): more crypto-only ideas
Details are in `research/GEN63_MORE_CRYPTO.md`.

- **Rejected:** C\* on 20 coins (worse than 10), cascade with risk-based sizing, premium carry with trend-aligned legs.
- **Dip-buy in uptrends:** passes its own test but lowers the portfolio's 2022–26 Sharpe, so it is not added.
- **Near-miss: 4-hour breakout trend (BTC/ETH/SOL, long-short).** It earns in 2022 and lifts the portfolio from 1.56 to 1.69 (65% positive months). Forward-test candidate.

## Gen64–65 (2026-10-15): own ideas round 2 and literature-based crypto ideas
Details are in `research/GEN64_OWN_IDEAS_2.md` and `research/GEN65_LITERATURE_CRYPTO.md`.

- **Nothing passes.** Rejected: 4h/12h trend ensembles, BTC-to-alt lead-lag, own-history ranking.
- **6h trend with coin selection:** good alone (2023+ 1.19) but correlation 0.59 with C\*.
- **Friday options-expiry window (maker):** 2023+ 1.13, but DEV slightly negative and only 12 trades a year. Forward-test lead only.

## Gen66 (2026-10-15): prop risk tools for the crypto portfolio
Details are in `research/GEN66_PROP_TOOLS.md`.

- **Daily portfolio stop at 50% of the firm's daily limit:** +$3–5k net per $100k account over 2 years at HyroTrader and CFT, and 0 daily-loss fails. At SizeProp the unlucky-10% net is $240 lower, so it misses the all-four rule by a hair.
- **Cushion scaling:** clearly worse.

## Gen67 (2026-10-15): stress tests and execution
Details are in `research/GEN67_STRESS_EXECUTION.md`.

- **ADOPTED: cascade with a -0.5% limit entry.** 2023+ 1.35 (was 1.19); 2022 turns positive (+0.77 Sharpe).
- **Crypto-firm portfolio v2:** Sharpe 1.83 (2022–26), 67% positive months, 2022 +8%.
- **S50 daily stop** now helps at all four crypto firms.
- **Bootstrap expectation at HyroTrader 1-Step:** $20.7k per $100k account over 2 years (unlucky 10%: $5.6k), P(profit) 98%.
- **Rejected:** C\* weekly rebalance, no-trade band.

## Gen68 (2026-10-15): fill realism and drawdown control
Details are in `research/GEN68_FILLS_DRAWDOWN.md`.

- **Cascade limit fills:** the gain survives a 0.1% trade-through rule (2023+ 1.30), but not 0.3%. The portfolio now uses the strict version.
- **Maker rebalancing for C\* / premium carry:** rejected (adverse selection).
- **Portfolio vol targeting: ADOPTED.** Max DD -20% to -13.5%; bootstrap 5%-worst year +0.4% to +3.0%.
- **Crypto-firm portfolio v3:** Sharpe 1.88, max DD -13.3%.
- **At HyroTrader 1-Step (bootstrap):** $20.3k per $100k account over 2 years, unlucky 10% $6.8k, P(profit) 98.5%, payout months 52%.

## Gen69 (2026-10-15): portfolio v4
Details are in `research/GEN69_V4.md`.

- **v4** (C\* + premium carry + strict-limit cascade + 4h trend, vol targeting): Sharpe 1.95, max DD -12%, 68% positive months, 2022 +8%.
- **Vol targeting:** the drawdown benefit is robust; the Sharpe benefit is not, because the 14d neighbour fails.
- **Friday-expiry window:** forward test only, because its tail risk cannot be estimated.
- **Look-ahead bug in the first hourly 4h sleeve:** caught by its impossible result and fixed.
- **Prop (bootstrap), HyroTrader 1-Step at 1.0 / 0.6:** $22.5k per $100k account over 2 years, unlucky 10% $7.5k, P(profit) 98%.

## Gen70 (2026-10-15): uploaded papers 1, 2, 3, 5 with exact full-text rules
Details are in `research/GEN70_PAPERS.md`.

- **Weiss expiry reversal, last Friday:** fade 07–08 UTC from 08:00 to 10:00.
  - **Passes the gate:** DEV 0.47, TEST 1.64, HOLD 0.62, corr 0.
  - **v4 + it:** Sharpe 1.94 → 2.29.
  - **Evidence is thin:** 81 events, t = 1.6.
  - **v5 candidate at notional cap 0.5:** Sharpe 2.20, max DD -9.9%. Paper trading first.
- **Rejected:**
  - AdaptiveTrend: HOLD -1.15, corr C\* 0.61.
  - Dhanya own-history books: TEST 0.50; mostly the carry we already hold.
  - CTREND exact: TEST -1.61; a small-cap effect.

## Gen71 (2026-10-15): uploaded papers 6-9
Details are in `research/GEN71_PAPERS.md`. All rejected.

- **Zarattini Donchian ensemble:** HOLD 0.01, corr C\* 0.66. As a replacement for C\* it lowers v4 to 1.77.
- **Guo cross-crypto lead-lag:** gross Sharpe ~5 at 5 minutes, but strongly negative after costs. Not tradable, and not allowed at prop firms.
- **Borri CMOM:** TEST 0.14.
- **Gornall perps/basis:** not applicable (needs a spot leg).
- **v4 + Weiss expiry (v5 candidate)** remains the best crypto portfolio.

## Gen72 (2026-10-15): optimisation, final crypto portfolio v5
Details are in `research/GEN72_OPTIMISE.md`; the chart is `results/gen72_report.png`.

- **Sleeve tuning (104 cells, plateau rule + walk-forward):**
  - Every tuned sleeve was worse out of sample: premium carry 0.87 → 0.69, trend 4h 0.93 → 0.87, cascade 1.30 → 0.91.
  - **Defaults kept.**
- **Portfolio scaling:** now point-in-time (P1 equal risk), so the small look-ahead in the old recipe is gone.
- **v5 = v4 + Weiss expiry at half weight:**
  - Sharpe 2.25, Sortino 4.3, CAGR 38.7% at 15% vol, max DD -9.5%.
  - 72% positive months; worst month -4.2%; 2022 +18.8%.
  - Treat this as an in-sample best case: plan for a live Sharpe of 1.3-1.7.
- **HyroTrader 1-Step 1.0 / 0.6 (bootstrap):** $26.4k per $100k account over 2 years, unlucky 10% $12.0k, P(profit) 99.6%.

## Gen73 (2026-10-15): first CFD tests on Dukascopy hourly data
Details are in `research/GEN73_CFD_FIRST.md`. **All rejected.**

| Test | Result |
|---|---|
| Gold session split | +0.76 in 2013-15, -0.72 since: decayed |
| European-open re-test | fresh -0.71 |
| Noise-area re-test | fresh -0.59 |
| 4h trend on 6 CFDs | -0.41 |
| Overnight US100 | fresh +0.90, but it fails the frozen same-sign rule and is mostly equity beta |

**Next for CFD firms:** crypto CFDs (C\* / trend / Weiss with CFD costs) and the FX fix, once the rest of the Dukascopy data is in.

## Gen74 (2026-10-15): crypto portfolio as CFDs at CFD firms
Details are in `research/GEN74_CRYPTO_CFD.md`.

- **Surviving CFD costs (spread + swap, no funding):** only C\* and Weiss expiry.
  - The 4h trend misses 2025-26.
  - Premium carry and the cascade fail.
- **C\* + Weiss as CFDs:** Sharpe 1.50, max DD -16%, 49% positive months.
- **FTMO / FundedNext / BrightFunded 2-Step at 1.0 / 0.6:**
  - $14-15k mean net per $100k over 2 years;
  - unlucky 10% about $0-1.4k;
  - P(profit) 90-92%.
- **Verdict:** a weaker second channel next to the crypto firms (v5: $26.4k, 99.6%).

## Gen75-76 (2026-10-15): index / gold ideas, batches 2-3
Details are in `research/GEN75_76_INDEX_GOLD.md`.

- **14 more trials, all rejected:** RSI(2) pullback, pre-FOMC drift, gold London fix, Asian-range breakout, vol-managed equity, option-expiry week, cross-index reversal.
- **Near misses** (forward-test list only, not adopted):
  - RSI(2) pullback: HOLD 1.29, TEST 0.39;
  - pre-FOMC drift: TEST 1.15, HOLD 0.38.
- **Gen73-76 total:** 19 index / gold / FX timing ideas, none survives CFD costs on 2013-26 data.

## Gen77 (2026-10-18): full Dukascopy set
Details are in `research/GEN77_DUKASCOPY_FULL.md`.

| Test | Result |
|---|---|
| FX fix | tiny effect (<1 bp/day) under 4 bp/day costs; rejected |
| Month-end overlay | rejected |
| Noise-area on 5-minute data | US100 fresh 0.44 (near miss), US500 fresh -1.15 |
| Dukascopy BTC/ETH | correlation 0.94-0.96 with Binance; **Gen74 crypto CFD book confirmed** |

**Total so far:** 25 non-crypto CFD ideas, none passes.

## Gen78 (2026-10-18): low-turnover CFD ideas + the CFD-firm portfolio
Details are in `research/GEN78_CFD_PORTFOLIO.md`.

- **Rejected:** XS momentum (-0.71), pairs (-0.51), FX seasonality (-0.54). That makes 31 non-crypto CFD ideas, none passing.
- **CFD-firm portfolio = crypto CFD book (C\* + Weiss):**
  - Sharpe 1.57, max DD -16%, 47% positive months;
  - FTMO / FundedNext / BrightFunded at 1.0 / 0.6: $15.0-15.8k mean net per $100k over 2 years, P(profit) 91-92%.

## Gen79 (2026-10-18): per-firm prop deployment optimisation
Details are in `research/GEN79_PROP_DEPLOYMENT.md`. Picked on 2022-24, verified on 2025-26.

| Firm | Adopted setting | 2025-26 mean net (pick vs default) | Note |
|---|---|---|---|
| HyroTrader 1-Step | 1.25 / 1.0 / 60% | $26.8k vs $17.8k | |
| HyroTrader 2-Step | 1.5 / 1.0 / 50% | $27.6k vs $14.9k | |
| FTMO / FundedNext / BrightFunded (CFD book) | 1.5 / 1.0 / 60% | about $20k vs $10.5-11.3k | safer as well |
| SizeProp, CFT | defaults kept | | pick failed the 2025-26 check |

## Gen81-83 (2026-10-18): CFD-book improvements
Details are in `research/GEN81_83_CFD_BOOK.md`.

- **Rejected:**
  - C\* rebalance band: no effect; turnover is already low.
  - CME weekend gap: -0.36.
  - 5-minute ORB on US100: 2024-26 0.06; fails at 2 bp.
- **NEW: swap-free CFD book** (C\* + premium carry + trend 4h + Weiss; same sleeve rule at zero swap):
  - Sharpe 1.81, max DD -12.8%, 67% positive months;
  - FTMO / FundedNext / BrightFunded at 1.5 / 1.0 / 60%: about $35k mean net per $100k over 2 years, unlucky 10% about $12k, P(profit) 98%.
  - Usable only where crypto CFDs carry no swap.

## Gen84 (2026-10-18): new crypto Sharpe ideas, all rejected (5 trials)
Details are in `research/GEN84_SHARPE_IDEAS.md`.

- **Rejected** (yearly-scaled daily Sharpe):
  - MAX/lottery effect: TEST -0.63;
  - idiosyncratic vol: TEST -0.99;
  - turn-of-month: TEST -1.15;
  - DVOL VRP overlay on v5: 2.26 vs 2.275, deeper DD.
- **v5 unchanged** at 2.275.
- **Swap-free:** FundedNext offers swap-free at +10% fee, which costs about $50 of mean net. It is the practical home for the swap-free CFD book.

## Gen85 (2026-10-18): CFD-book improvements (8 trials)
Details are in `research/GEN85_CFD_IMPROVE.md`.

- **ADOPTED: swap-aware C\*** (drop coin weights below half the average held weight):
  - C\* as a CFD: HOLD 0.39 -> 0.50;
  - CFD book: Sharpe **1.57 -> 1.62**;
  - FTMO / FundedNext / BrightFunded at 1.5 / 1.0 / 60%: about $26-28k mean net per $100k (+$0.5-1k).
- **Rejected:**
  - Weiss on 11 CFD coins: HOLD 0.11;
  - trend 4h on 11 CFD coins: HOLD -0.41.

## Gen86 (2026-10-18): more CFD sleeves, all rejected (6 trials)
Details are in `research/GEN86_CFD_SLEEVES.md`.

- **Rejected:**
  - CME expiry fade: TEST -0.08, HOLD 1.77; on the watchlist;
  - crypto weekend -> Monday index: HOLD -0.78;
  - pre-FOMC drift on BTC/ETH: TEST 0.20.
- **CFD book unchanged** at 1.62.

## Gen87 (2026-10-18): crypto sleeves re-tested in the CFD book, all rejected (4 trials)
Details are in `research/GEN87_CFD_RETEST.md`.

- **Rejected:**
  - dip-buy: passes alone (TEST 0.93, HOLD 0.58) but lowers the CFD book to 1.58;
  - cascade on BTC/ETH: HOLD -0.82;
  - trend 4h on BTC/ETH: HOLD 0.05.

## Gen89-90 (2026-10-18): NEW SLEEVE, the deleveraging bounce (6 trials)
Details are in `research/GEN89_90_DELEV_BOUNCE.md`.

- **Rule:** BTC/ETH open interest -10% in 24h with a falling price -> long 2 days.
  - DEV 0.70, TEST 1.01, HOLD 0.61, corr C\* 0.03.
  - 70 episodes, t = 2.2. A few big rebounds carry much of it.
- **CFD book:** Sharpe **1.62 -> 1.80**, max DD -16% -> -12%; FTMO / FundedNext / BrightFunded at 1.5 / 1.0 / 60% about **$31-32k** mean net.
- **Swap-free book:** **1.81 -> 2.07**; FundedNext swap-free about **$42k**.
- **Crypto v5 + it:** **2.28 -> 2.46** (candidate v6).
- **Rejected in the same round:**
  - NFP-day crypto momentum;
  - weekend reversal;
  - US500 trend filter on C\*.

## Gen91-92 (2026-10-18): open-interest family and capitulation signals, nothing new adopted (8 trials)
Details are in `research/GEN91_92_OI_CAPITULATION.md`.

- **Bounce on altcoins:** positive on 7 of 9 coins. It confirms the effect but is not a sleeve (10 bp spreads).
- **Rejected:**
  - short-covering fade;
  - leverage build-up fade;
  - DVOL spike bounce;
  - volume capitulation (too few signals);
  - VIX-backwardation index bounce (passes alone, lowers the book).
- **Candidate v6 (v5 + bounce):** Sharpe 2.46; HyroTrader 1-Step about **$46k** mean, unlucky 10% $18.8k (v5: $41.9k / $14.0k).

## Gen93 (2026-10-18): forced-flow family (3 trials)
Details are in `research/GEN93_FLOWS.md`.

- **Stablecoin mint spike** (USDT+USDC +0.5% in a day -> long BTC/ETH 3 days): passes the rule (1.01 / 1.79 / 0.33; book 1.80 -> 1.88).
  - Not adopted: HOLD turns negative at every nearby threshold.
  - Moved to the watchlist.
- **Rejected:**
  - perp deep-discount bounce;
  - funding flush (passes alone, lowers the book).

## Gen94 (2026-10-18): bounce-family ensemble and 4-hourly bounce, rejected (2 trials)
- The daily H4 deleveraging bounce stays.
- **Ensemble of all 6 bounce rules:** book 1.27.
- **4-hourly check:** HOLD 0.26.

## Gen95 (2026-10-18): CFD cost structure, no change (3 trials)
- **Rejected:**
  - C\* on BTC/ETH only: book 1.61;
  - C\* with altcoins at half weight: 1.80, no gain;
  - risk-sized bounce: 1.77.

## Gen96 (2026-10-18): validation and risk audit of the CFD book
Details are in `research/GEN96_VALIDATION.md`.

- **Look-ahead:** 0 differences in about 244k rows at 5 data cutoffs. A deliberate look-ahead control is detected (2.59).
- **Execution delay:** C\* and the bounce are robust; **Weiss must be on time** (1h late: book 1.57).
- **Bootstrap 2y Sharpe:** 5-95% range 0.69-2.96; P(2y loss) 0.5%.
- **Deflated Sharpe probability:** 0.81 at 700 trials, 0.57 at 7,000.
- **Crashes:** FTX -6.2%, LUNA -0.6%.
- **Cost stress:** 2x spread + 2x swap still 1.45.
- **Bounce grid:** a 10-12% ridge; the registered cell is the best one, so expect less live.
- **Realistic live CFD Sharpe: about 1.2-1.6.**

## Gen97 (2026-10-18): forced-flow family II, rejected (2 trials; `config/gen97_protocol.json`, `scripts/gen97_flows2.py`)
- **Taker sell climax:** DEV 2022 -0.33, TEST 1.74, HOLD -0.19; book 1.78.
- **Market-wide deleveraging (OI of all 20 coins -8%):** DEV -0.98, TEST 0.90, HOLD 0.64; book 1.74.
- The per-coin H4 bounce stays the only adopted forced-flow sleeve.

## Gen98 (2026-10-18): slow bounce and gold trend, rejected (2 trials; `config/gen98_protocol.json`, `scripts/gen98_slow.py`)
- **Weekly deleveraging bounce** (OI -20% in 7 days): DEV 2022 -0.06, TEST 1.38, HOLD -0.55; book 1.45.
- **Gold 12-month trend (XAUUSD CFD, long-only, 10% vol):** DEV 2014-19 0.12, TEST 2020-23 0.19, HOLD 2024-26 1.71; Yahoo 2005-12 pre-check 0.76.
  - It raises the book to 1.86, but only through the 2024-26 gold rally.
  - Rejected by the TEST rule; that one-period dependence is exactly what the rule is there to catch.

## Gen99 (2026-10-18): altcoin bounce in the cheaper books, rejected (2 trials; `config/gen99_protocol.json`, `scripts/gen99_altbounce.py`)
- **Swap-free CFD book:** alt bounce DEV 2022 -0.15, TEST 1.01, HOLD 0.46; book 2.07 -> 2.02.
- **v6 at perp costs:** alt bounce DEV 2022 -0.10, TEST 1.12, HOLD 0.73; v6 2.46 -> 2.50.
  - Rejected: DEV < 0.
  - The altcoin bounce lost money in 2022 in every form tested (Gen91, Gen99), so the rule keeps it out.

## Gen88 + Gen101 (2026-10-19): Coinbase premium, ADOPTED for the CFD books (4 trials)
Details are in `research/GEN88_101_COINBASE.md`.

- **The rule was registered before the data existed.**
  - Coinbase-vs-Binance premium z > 1 -> long, z < -1 -> short, for 1 day, BTC/ETH.
  - DEV 0.57, TEST 1.12, HOLD 0.50, corr C\* -0.04; placebo p = 0.01; clocks aligned (0.998 at lag 0).
- **CFD book:** 1.80 -> **1.85**.
- **Swap-free book:** 2.07 -> **2.15**.
- **Crypto v6:** passes but adds only 0.01, so v6 is unchanged.
- **C\* premium filter:** rejected.

## Gen102 (2026-10-19): more demand-flow signals (5 trials)
Details are in `research/GEN102_FLOWS.md`.

- **Rejected:**
  - Coinbase premium on altcoins: HOLD -0.55;
  - Fear & Greed: HOLD -0.24.
- **Kimchi premium momentum:** DEV 0.40, TEST 0.80, HOLD 1.29 alone (contrarian strongly negative), but it lowers the book (1.85 -> 1.70), so it is not adopted.
- **Bitstamp replicates the Coinbase premium** (corr 0.93): the effect is a USD-vs-USDT/perp basis signal, not exchange-specific.

## Gen105 (2026-10-19): demand composite (Coinbase + Korean premium), not adopted (1 trial)
Details are in `research/GEN105_DEMAND_COMPOSITE.md`.

- **The checks found an FX-timing error.** Yahoo stamps USD/KRW at London midnight. It inflated the first run (BrightFunded book 2.45) and Gen102's kimchi numbers.
- **Strict point-in-time version:**
  - sleeve 1.20 / 1.37 / 1.11 (Coinbase sleeve 0.72 / 1.33 / 0.70);
  - book 2.25 -> 2.30;
  - placebo p < 0.02.
- **Not adopted:** book TEST falls 3.45 -> 3.33, which breaks the rule.
- **Watchlist.**

## Gen106 (2026-10-19): web-sourced intraday ideas at BrightFunded costs, rejected (3 trials; `config/gen106_protocol.json`, `scripts/gen106_intraday.py`)
- **Hourly opening order imbalance** ("Quarter-Hour Effect", arXiv 2607.09426): DEV 0.26, TEST -0.69, HOLD -1.47. Top-20% variant: -1.80 / -1.02.
- **16:00 London fixing reversal** ("tea time", Brauneis, Mestel & Theissen 2025): -2.21 / -2.52 / -3.01.
  - Strongly negative in every period, so the opposite (continuation after the 15:00-16:00 London move) looks positive.
  - That observation was made on this data, so it cannot be tested on this data.
  - **Forward-test only.** Watchlist: "fixing continuation", to be judged on fresh data from 2026-10 onward.

## Gen107 (2026-10-19): cost-sensitive rules re-tested at BrightFunded's real costs, rejected (2 trials; `scripts/gen107_bfcost.py`)
- **Cascade strict on BTC/ETH** (1.6 / 3.9 bp per side): -0.08 / 0.05 / -0.78. Lower costs do not rescue it.
- **Hourly shock reversal:** 0.43 / -0.58 / -0.75.

## Gen108 (2026-10-19): walk-forward machine learning (2 trials)
Details are in `research/GEN108_ML.md`.

- **Ridge on 16 point-in-time features:** sleeve 0.27 / 1.49 / 1.49; book 2.25 -> 2.28, HOLD 1.55 -> 1.95.
  - Not adopted: book TEST 3.45 -> 3.42 breaks the "not lower" rule.
  - Watchlist.
- **Gradient boosting:** TEST -0.40, rejected.

## Gen109 (2026-10-19): ML in the crypto-firm book. ADOPTED candidate v7 (2 trials)
Details are in `research/GEN109_ML_V6.md`.

- **Walk-forward ridge** (16 point-in-time features: flows, premiums, OI, funding, taker flow, price):
  - in v6 at perp costs: sleeve 0.13 / 1.28 / 1.36, corr C\* 0.19;
  - **v6 2.46 -> 2.53** (TEST 3.44 -> 3.49, HOLD 1.90 -> 2.24).
  - Insensitive to alpha and refit frequency; placebo p < 0.01; survives 2x costs.
  - The flow features carry it. Weak 2021-22.
- **Cross-sectional ridge on 20 coins:** TEST -1.50, rejected.

## Gen110 (2026-10-19): more ML, rejected (2 trials; `config/gen110_protocol.json`, `scripts/gen110_ml2.py`)
- **Hourly ridge, 4h horizon, BTC/ETH:** 0.80 / 1.34 / **-0.26**; v7 2.53 -> 2.39.
- **Daily ridge pooled over 9 altcoins:** 0.38 / 1.17 / **-0.32**, corr C\* 0.36; v7 -> 2.32.
- Only the daily BTC/ETH ridge (Gen109) holds up out of sample.

## Gen111 (2026-10-19): cross-exchange signals, rejected (2 trials; `config/gen111_protocol.json`, `scripts/gen111_xexch.py`)
- **Binance-vs-Deribit funding divergence (contrarian):** 0.46 / **0.09** / 0.99.
  - v6 2.46 -> 2.53 and bf 2.25 -> 2.35 overall, but TEST fails and book TEST falls.
- **OKX-vs-Binance perp premium momentum:** 0.32 / 0.37 / -0.65.

## Gen113 (2026-10-19): sleeve allocation, rejected (4 trials)
Details are in `research/GEN113_ALLOCATION.md`.
- ERC (2.33 v6 / 2.13 bf), min-variance (2.11 / 1.88), 90-day inverse vol (1.82 / 1.91) and a Sharpe tilt (2.06 / 1.91) all lose to the current P1 equal-risk weights (2.46 / 2.25).
- **P1 stays.**

## Gen116-117 (2026-10-19): equity-session spillover, volume-return rule, CFD intraday ideas; all rejected (7 trials)
- **Gen116 (crypto):** US-open spillover into BTC/ETH 0.24 / 0.17 / -1.25 (perp DEV/TEST/HOLD); US-close spillover 0.04 / -1.18 / -1.17; Llorente volume-return rule -0.49 / -0.36 / -0.13. All lower both books.
- **Gen117 (Dukascopy CFDs, CFD costs, DEV 2013-18 / TEST 2019-22 / HOLD 2023-26):** bond-equity lead -0.57 / -0.18 / -0.21; EIA crude day -0.19 / 0.17 / -0.06; FX month-end fix 0.69 / -0.45 / 0.17; overnight-intraday reversal -0.35 / -0.22 / 0.45. US500 and USTBOND data start in 2018 (short DEV). One deviation, noted: the CFD data has no 17:00 ET bar, so the night return starts at the 17:00 ET price instead of 18:00.

## Gen118 (2026-10-19): on-chain signals (Coin Metrics), rejected (4 trials)
- **O1 exchange net flow:** sleeve 2020-22 / 23-24 / 25-26 = -0.56 / 0.45 / 1.61; it would lift v6 2.46 -> 2.64 and bf 2.25 -> 2.44, but the sleeve fails its own DEV and TEST bars. **Rejected; watchlist only.** Extra caution: Coin Metrics re-labels exchange addresses after the fact, so historical flows can contain look-ahead that a live trader would not have seen.
- **O2 exchange supply trend:** 0.00 / -0.22 / -0.41. **O3 fee mania:** -1.21 / -0.63 / no HOLD signals. **O4 hash ribbons:** 1.00 / 0.39 / -1.32.

## Gen114-121 (2026-10-20): Databento futures, Binance extra coins, BrightFunded breadth (16 trials)
Details are in `research/GEN114_121_NEW_DATA.md`.
- **Futures:** all 12 rejected. T1 trend+carry 0.04 / -0.16 / -0.41 (after fixing a carry-ordering bug); best U5 XS momentum 0.50 / 0.23 / 0.36. No futures book.
- **CME bitcoin:** basis momentum and the "CME gap fill" both rejected (gap fill TEST -2.34).
- **Premium carry on 60 coins (Gen80):** v6 2.458 -> 2.539, HOLD 1.90 -> 2.39, robust to 2x costs and to dropping any top coin. But v6 TEST falls 3.44 -> 3.14, so it fails the strict book rule. **Forward-test candidate.**
- **Premium carry on 42 BrightFunded coins (Gen121):** bf 2.252 -> 2.414, HOLD 1.55 -> 2.09, but TEST 3.45 -> 3.18. Same verdict.
- **Bounce on all altcoins (Gen112):** DEV 2022 -0.30. Rejected; per-coin means replicate (+0.74% per episode on the extra coins).
- **Cascade on 60 coins (Gen80):** sleeve 2023-26 1.30 -> 0.90, v6 2.46 -> 2.32. Rejected.
- **Shadow paper tests v6b and bf-b started** (premium carry breadth); v6 and bf stay the main books.

## Gen122-123 (2026-10-20): futures rounds 2-3 (8 trials)
Details are in `research/GEN122_123_FUTURES.md`.
- **Only F5 (vol-managed long ES/NQ) passes:** 1.05 / 0.55 / 0.98. It is equity beta (buy-and-hold: 1.07 / 0.47 / 1.17) with a smaller drawdown (-22% vs -35%).
- **Rejected:** European-open drift, month-end Treasuries (dead since 2023), FX carry, TSMOM 12m (0.26 / 0.42 / 0.39), in-session vol-managed equity, risk parity.

## Gen119 (2026-10-20): CFTC COT positioning, rejected (4 trials)
- **Data fix first:** the report dates sit in different columns and formats across the yearly CFTC files. Before the fix gold had only 3 years and CME bitcoin none; after it, full 2010-2026 coverage.
- **Results:**
  - C1 managed-money extremes, commodities: -0.35 / -0.73 / -0.69
  - C2 leveraged funds, financials: 0.04 / 0.61 / -0.52
  - C3 hedging pressure: -0.04 / -0.78 / 0.82
  - C4 CME bitcoin leveraged funds -> crypto: -0.02 / 0.24 / -0.78; lowers v6 2.46 -> 2.29 and bf 2.25 -> 2.09.

## Gen124 (2026-10-20): intraday news-minute continuation and gap fade (3 trials; CFD replication run first)
- **Timestamps:** Dukascopy 5-minute bars are labelled by their start (the volatility peaks sit in the 08:30 and 09:30 bars).
- **CFD US500/US100, 1 bp per side, DEV 2018-20 / TEST 2021-23 / HOLD 2024-26:**
  - J1 08:30 continuation: 0.76 / -0.60 / -0.84 (516 trades)
  - J2 14:00 continuation: -0.82 / -0.81 / -0.11
  - J3 RTH gap fade: 0.92 / -1.08 / 0.82
- **Verdict:** J1 and J2 already fail the registered rule, which requires a non-negative CFD replication. The futures 1-minute run follows when the data arrives.

## Gen124-126 (2026-10-20): intraday futures on 1-minute ES/NQ
Details are in `research/GEN124_126_INTRADAY_FUTURES.md`.
- **News-minute continuation and gap fade:** rejected on both futures and CFD data (consistent).
- **Noise-area breakout on real futures:** ES+NQ primary 0.92 / 1.17 / 0.16, so rejected (HOLD). The NQ component alone is 1.05 / 1.07 / 0.88 (11% a year at 11% vol, max DD -9%, corr v6 0.05). Choosing NQ afterwards is selection, so it is pre-registered for an out-of-sample check on unseen NQ 2010-2017 data (Gen126).
- **ORB 5-minute and month-end pension rebalancing:** rejected.

## Gen126-127 (2026-10-20): NQ out-of-sample, multi-sleeve futures/CFD round (9 trials)
- **Gen126, NQ noise-area on unseen 2010-17 data:** net -0.45 (both halves negative), so **rejected**. Gross it is +0.82; at 0.5 bp it is 0.48. The edge is real but thin; NQ's lower prices before 2018 made costs 1.9 bp per side.
- **Gen127 results:**
  - P1 IBS reversal, index futures: 0.00 / 0.68 / 0.16
  - P2 gold/silver: -0.04 / -1.06 / -0.37
  - P3 gasoline crack: -0.20 / 0.51 / -0.15
  - P5 Baltussen last half hour: 0.41 / -0.02 / -2.25
  - P7 IBS on index CFDs: - / 0.63 / 0.08
  - P8 Nasdaq-vs-S&P style momentum: -0.17 / 0.03 / -0.56
- **P4 Brent-WTI reversion on Dukascopy CFDs: 0.63 / 0.73 / 0.73 (passes).** But Dukascopy WTI contains roll gaps (21 bp median deviation from roll-safe CME on roll days), so it is **not accepted** until the clean CME BZ/CL test (Gen128).
- **Gen128, clean-data check of P4 on CME BZ/CL:** -0.63 / -0.01 / -0.49. **P4 rejected: the Dukascopy result was a roll-gap artefact.**
- **Gen129 Goldman-roll front-running (user paper):** rejected (energy -0.54 / -0.57 / -0.30; gross about 0). Details are in research/PAPERS_2026-10-20.md.
- **Gen130 Treasury auction cycle (ZT/ZF/ZN/ZB, 1,076 auctions):** A1 short before 0.02 / 0.25 / 0.67; A2 long after 0.46 / 0.33 / -0.34; A3 round trip 0.40 / 0.47 / 0.26. Positive in every period but below the bar, so rejected (near-miss).
- **Gen131-132 (user papers):**
  - Crypto order-flow cross-section: sleeve 2.05 / 0.99 / 0.60, v6 2.458 -> 2.557, but HOLD 1.901 -> 1.879 (fails the strict rule). 2026 so far -1.87. In bf: HOLD -1.11. **Rejected; the effect is fading.**
  - CME bitcoin retail positioning: rejected.
  - Post-FOMC drift: waits for the FOMC dates.
- **Gen131 F1 post-FOMC drift (ZN/ZB, 124 events):** 0.60 / -0.63 / 0.30. Rejected.

## Gen133 (2026-10-20): combining tested crypto improvements (3 trials)
- **v7 = v6 + ridge ML:** 2.534 / TEST 3.494 / HOLD 2.240. **Passes the strict rule** (as Gen109).
- **v8 = v7 + 60-coin premium carry:** 2.617, but TEST 3.295. Fails vs v6 and vs v7.
- **bf-b + ridge:** 2.438, TEST 3.241. Fails.
- **Reading:** breadth always lowers 2023-24 and stays shadow-only. **v7 is the validated crypto improvement**, now to be built for paper trading.
- **Gen134 noise-area improvement round:** selected V1 (60-minute checks, DEV 2018-23 1.10). Judgement: ES+NQ 2024-26 **-0.20**, NQ 2010-17 **-0.85**. **Rejected for good.**

## Gen135 + P6 (2026-10-20): first passing futures book; bf improvement
- **Futures book (Gen135):** nested out-of-sample. 5 sleeves selected on 2010-22 only (F3, F5, G1, P1, A3); 2023-26 Sharpe **0.59** (pass), 6.4% a year at 10% vol, max DD -9.9%, corr v6 0.04. MFFU/Tradeify fit (overnight).
- **bf + P6 vol-managed US100/US500 CFDs:** bf 2.252 -> **2.302**, TEST 3.45 -> 3.69, HOLD 1.55 -> 1.85. **Passes the strict rule** (2022 weaker: 1.15 -> 0.46).
- **v7 (v6 + ridge ML):** 2.534, passes. The validated crypto improvement.
- **Gen136 futures round 5:** basis-momentum -0.76 / 0.70 / 0.42; skewness -0.03 / 0.36 / 0.12; weekly XS reversal -0.50 / -0.57 / -0.12; bond trend -0.19 / 0.94 / 0.01; curve trend -0.47 / 0.01 / -0.13. All rejected.
- **Gen137 crypto sleeves on CME BTC/ETH futures:** all 6 fail. The code reproduces the Binance results (e.g. C* legs 1.91 / 2.02 / 0.67 on Binance vs 1.28 / 1.44 / 0.39 on CME weekend-hold, 0.80 / 0.81 / 0.19 weekend-flat). Topstep daily-flat is negative for all. Causes: weekend closure, thin off-hours CME prints.
- **Gen138 walk-forward ridge across 24 futures:** 0.44 / -0.31 / -0.53. Rejected.
- **Gen139 vol-managed gold:** bf+P6+gold 2.511 (TEST 3.75, HOLD 2.43) passes the strict bf rule, but the 16-year GC version fails DEV (-0.04 / 0.28 / 1.12). **Shadow only**: the strength is the 2023-26 gold rally.
- **Futures book (Gen135):** all 5 selected sleeves are positive in 2023-26, and the book is positive in every unseen year (0.35 / 0.62 / 0.60 / 0.83).
- **Gen140 nested optimisation of the futures book:** settings and construction tuned on 2010-22 only (54 trials); judged once on 2023-26: **0.661 vs 0.579** (reference, same code). Adopted. Chosen: F5 vol window and cap per grid, P1 IBS long-only 0.3/0.7 (2023-26 0.94), A3 pre 5 / post 4, G1 126 days (2023-26 -0.66: an example of why we judge out of sample), Sharpe-weighted construction.
- **Gen141 IBS per asset group:** only rates qualified on 2010-22 (0.46), and they were -0.34 in 2023-26. Book 0.577 < 0.661, **not adopted**.
- **Gen142 overnight drift grid (Topstep-compatible):** chosen ES/NQ/RTY/YM 20:00-09:00 ET, tuned 0.14, 2023-26 0.32 stand-alone; book 0.654 < 0.661, not adopted.
- **Gen143 nested tuning of the other families:** entrants U5 XS momentum (252 days, 6 per side; tuned 0.36, 2023-26 0.36) and K3 pension rebalancing (5 days; 0.57 / 0.12). Book 2023-26 **0.674** > 0.661, **adopted**. Not entering: basis-momentum, post-FOMC hold, COT thresholds.
- **Current futures book (7 sleeves: F3, F5, G1-126, P1 long-only IBS, A3, U5, K3), Sharpe-weighted on 2010-22:** out of sample 2023-26 **0.674**.
- **Gen144 event effects (DEV / TEST / HOLD):**
  - J8a pre-FOMC intraday: 0.34 / 0.20 / -0.54 (NQ 2010-17 -0.77)
  - J8b post-FOMC continuation: -0.42 / -0.36 / 0.27
  - J4 OPEX pinning fade: 0.17 / -0.51 / -0.82
  - J5 leveraged-ETF rebalancing on big days: -0.06 / -1.14 / -1.16
  - J8c daily pre-FOMC ES 2010-26: 0.21 / 0.21 / -0.53
  - **All rejected.**

## Gen145-146 (2026-10-20): classic families; the equity dip-buying ensemble enters
- **Gen145 (19 trials), none enter (best tune 2010-22 / 2023-26):** value XS 5y -0.21 / -0.73; seasonality XS -0.10 / -0.34; multi-speed EWMAC trend 0.23 / -0.44; 52-week high 0.10 / 0.10; continuous carry 0.11 / -0.41.
- **Gen146 (13 trials):**
  - **R1 reversal ensemble on ES/NQ/RTY/YM** (mean of RSI2 < 10, 5-day low, 3 down closes, IBS < 0.3; long only, next-close exit): **0.68 / 1.09**. Per index (2023-26): ES 1.21, NQ 1.34, RTY 0.76, YM 0.62.
  - T1 turn of month (2 before, 3 after): 0.35 / 0.36.
  - T2 pre-holiday (1 session): 0.35 / 0.41.
  - **Book (Gen143 + R1, T1, T2) 2023-26: 0.825 > 0.674, adopted.**
- **Execution check (results/gen146_exec.json):** with a 1-day delay R1 collapses (0.13 / 0.55), so the edge needs entry near the close. Computing the signal **and filling at 14:00 ET** from hourly data (24h hold) gives **0.49 / 1.11** (12:00 1.13, 15:00 1.17, 16:00 1.32 out of sample). **The book with the executable 14:00 R1: 2010-17 1.49, 2018-22 1.31, 2023-26 0.815.** That is the number to quote.
- **Current futures book: 10 sleeves (F3, F5, G1, P1, A3, U5, K3, R1@14:00, T1, T2); out of sample 2023-26 0.815.**

## Gen147-151 (2026-10-20): R1 dip ensemble on other markets and holding windows
- **Gen147, R1 on US100/US500/US30 CFDs (14:00 ET fill) as a bf + P6 sleeve:**
  - Sleeve: 0.78 / 0.93 / 1.05 (2 bp: 0.72 / 0.81 / 0.99).
  - Book: 2.302 -> 2.065 (2022 0.46 -> -0.22). **Fails the strict rule.**
- **Gen148, where the R1 edge sits (ES+NQ 1-minute):**
  - 14:00 -> 16:00: -0.71 / -0.44 / -0.92.
  - **16:00 -> 09:30 overnight: 1.13 / 0.62 / 1.68** (NQ 2010-17 0.62).
  - Next session 09:30 -> 16:00: 0.73 / 0.49 / -0.02. **The Topstep version fails.**
- **Gen149, overnight R1 on unseen markets:**
  - RTY+YM futures: 0.04 / 0.63 / 0.35. **Fails.**
  - **US100+US500+US30 CFDs (5-minute): 0.85 / 0.98 / 1.54. Passes** (2 bp: 0.72 / 0.72 / 1.32).
  - The protocol required both sets to pass, so the futures book keeps the 24h R1.
- **Gen150, overnight R1 CFD sleeve for bf:** sleeve 0.51 / 1.00 / 0.81, book 2.302 -> 2.172. **Fails the strict rule.** Index sleeves beyond P6 dilute the crypto sleeves in the bf allocation.
- **Gen151, dip-day short 14:00 -> 16:00 on unseen markets:** RTY+YM -0.70 / -0.53 / -0.36; CFDs -0.29 / -0.50 / 0.29. **Rejected.**
- **Note for CFD-index accounts** (e.g. an index-only CFD challenge): overnight R1 on US100/US500/US30 is a validated stand-alone strategy (0.85 / 0.98 / 1.54 at 1 bp).

## Gen152-154 (2026-10-20)
- **Gen152, R1 dip ensemble by futures group (executable snapshot, 10 trials):** all groups negative on 2010-22 (rates -1.17, metals -0.58, energy -0.51, FX -0.90, ags -1.48). Even gross, none reaches 0.3 (rates 0.26, metals -0.13). **Dip-buying is an equity-index effect. Rejected.**
- **Gen153, calendar premia (8 trials):**
  - Announcement days: equities FOMC 0.26 / -0.50; bonds FOMC 0.03 / -0.17.
  - Options-expiry week: -0.13 / 0.48.
  - **Halloween (Nov-Apr long): 0.44 / 0.52, enters**, but the book drops to 0.777 < 0.815. **Not adopted.**
- **Gen154, intraday return periodicity, 26 futures hourly (9 trials):** net -12 to -27 (costs).
  - Gross 2.92 / 0.83: the signal is real, but the edge per unit of turnover (ES -0.1, NQ 0.1-0.8, GC 0.5-0.7, CL 1.1-1.8 bp) is below the cost per side (1.0-2.6 bp) in every market and setting. **Rejected: not tradable at our costs.**
- **Futures book unchanged: OOS 2023-26 0.815.**
- **Gen155, R1 refinement (12 trials, executable 14:00 ET):** chosen: base 4 indicators, size x vol250/vol20 (capped 2), 24h hold (tune 0.56, 2023-26 1.04). The 6-indicator and 48h-hold variants were worse on tune. **Book 2023-26 0.815 -> 0.842 (2010-17 1.46, 2018-22 1.33). Adopted.**
- **Gen156, book construction (walk-forward, 5 trials):** 2018-22 with 2010-17 weights: SW 1.21, MV50 1.29, MV80 1.26, SWC 1.26, HRP 1.12. Chosen MV50 -> 2023-26 **0.795 < 0.842. Not adopted**; Sharpe-weighting stays.
- **Gen157, market-neutral relative reversal NQ/RTY/YM vs ES (6 trials):** all negative on 2010-22 (-0.23 to -1.01). Rejected.
- **Gen158, flow effects (10 trials):**
  - Gotobi (USD/JPY into the Tokyo fix, 6J): tune 0.24, **2023-26 -1.63** (all settings -1.6 to -2.3).
  - Mid-month coupon reinvestment: best 0.19 / 0.23.
  - Nothing enters.
- **Gen159, FOMC cycle + mid-month flow (5 trials):**
  - FOMC-cycle weeks 2+4+6 long equities: 0.37 / 0.75 (all even weeks 0.19 / 0.83; week 0 only -0.24 / 0.38).
  - Mid-month [-1, +1] around the 15th: 0.72 / 0.37.
  - Both enter. **Book 2023-26 0.842 -> 0.908 (2010-17 1.53, 2018-22 1.36). Adopted. 12 sleeves.**
- **Gen160, sleeve-momentum overlay (walk-forward, 5 trials):** 2018-22 NONE 1.10, M126h 1.13, M504h 1.14, M252h 1.04, M252z 0.90. Chosen M504h -> 2023-26 **0.800 < 0.908. Not adopted.**
- **Gen161, vol-managed calendar sleeves:** const 0.70 / 0.80 vs vm 0.66 / 0.66 (tune / 2023-26). Const kept.
- **Gen162, sleeve upgrades:** F5 + 200d filter 0.64 / 0.80, + 100d 0.51 / 0.83 (current 0.84 / 0.98); K3 quarter-end 0.01 / -0.18. Current settings kept.
- **Gen163, big-move continuation (12 trials):**
  - **BC rates ZF/ZN/ZB (|z| > 2, hold 3 days, 1-day execution lag): 0.32 / 0.46, enters.** Commodities CC: 0.25 / 0.20, no.
  - **Book 2023-26 0.908 -> 1.041 (2010-17 1.57, 2018-22 1.46). Adopted, 13 sleeves.**
  - Sensitivity (report only): neighbouring BC settings give a book of 0.926-0.982 (th 1.5 / 2.5, H 2 / 4 / 5), and BC's correlation with the book is -0.17. **The gain is robust in sign, but 1.04 is the lucky top end; expect about 0.95.**
- **Gen164, flight-to-quality after ES drops (12 trials):** Treasuries best 0.18 / -0.10; gold best 0.04 / 0.73. Nothing enters.
- **Gen165, big-move continuation (12 trials):** equity up-days EU 0.48 / 0.25 enters, but the book is 1.035 < 1.041 (not adopted); FX all negative. Nothing adopted.
- **Gen166, seasonal energy spreads (2 trials):**
  - **Autumn heating-oil crack (long HO / short CL, Aug-Oct): 0.45 / 0.32 (2010-17 0.37, 2018-22 0.59), enters.** Spring gasoline crack 0.10 / 0.09, no.
  - **Book 2023-26 1.041 -> 1.102 (2010-17 1.63, 2018-22 1.56). Adopted, 14 sleeves.**
- **Gen167, seasonals (2 trials):** grain harvest pressure 0.17 / -0.22; gasoline grade switch -0.06 / 0.10. Rejected.
- **Gen168, bf with one merged index sleeve (3 trials):**
  - **M1 = P6 + R1 CFD: bf 2.302 -> 2.326, TEST 3.691 -> 3.698, HOLD 1.849 -> 1.883. Passes the strict rule; adopted as the new bf reference.**
  - M2 = P6 + calendar: 2.354, but HOLD 1.766. Fails.
  - M3 = all: 2.365, but TEST 3.684 and HOLD 1.796. Fails.
  - Calendar leg alone: 0.71 / 1.28 / 0.65.
- **Futures prop update (results/futures_prop_update.csv; bootstrap of the UNSEEN 2023-26 window only; 50k swing firm with ASSUMED terms):**
  - At risk 0.5: old book pass 33%, P(profit) 0.81, net 2y $2.4k; **new book (1.10) pass 59%, P(profit) 0.94, net 2y $4.3k (p10 +$671)**.
  - At risk 0.33: pass 89%, P(profit) 0.89.
- **Gen169, Treasury betting-against-beta (2 trials):** ZT+ZF vs ZB -0.61 / -0.08; ZT vs ZN -0.58 / -0.26. Rejected.
- **Gen170, open-interest growth (6 trials):** aggregate timing best -0.02 / 0.27; cross-section best -0.07 / -0.14. Rejected.
- **Futures book now: 14 sleeves (F3, F5, G1, P1, A3, U5, K3, R1 low-vol 14:00, T1, T2, FC, MM, BC, SH); out of sample 2023-26 1.102 (robust range given BC sensitivity about 1.0-1.05).**
- **Gen171, calendar effects on BTC/ETH as a v7 sleeve (2 trials):**
  - FOMC weeks 2/4/6: sleeve 0.21 / 0.63 / 0.74, v7 2.534 -> 2.548, but TEST 3.494 -> 3.258. Fails the strict rule.
  - Union of all calendar effects: 1.22 / 0.49 / -0.01. Fails.
- **Gen172, FOMC cycle in Treasuries / gold (2 trials):** Treasuries 0.13 / -0.47; gold 0.08 / 1.21 (fails the tune bar). Rejected.
- **Gen173, overnight-only calendar sleeves:** night 0.27 / -0.03 vs full 0.70 / 0.80. Full kept. **The calendar edge accrues in the session, not overnight.**
- **Gen174, Topstep calendar book (session only, flat overnight):** 1-minute ES+NQ -0.34 / 0.66 / -0.13; hourly 4-index 2010-17 -0.03. **Fails.** The calendar effects need the full close-to-close hold, and splitting the hold multiplies costs.
- **Gen175, international R1 legs in the bf index sleeve:**
  - DE40 -0.44 / 0.33 / 0.58, EU50 -0.51 / 0.74 / 0.51, UK100 -0.32 / -0.02 / 0.48, JP225 0.46 / 0.10 / 1.72.
  - Combined leg -0.31 / 0.36 / 1.07; book 2.331 but TEST 3.673 and HOLD 1.853. **Fails.**
- **Gen176 (2 trials):** post-winter HO crack -0.39 / 0.36; small-cap January effect -0.42 / 0.03. Rejected.
- **Gen177, book vol estimator (walk-forward, 5 trials):** 2018-22: R20 1.25, E30 1.22, MIX 1.20, R60 1.18, R120 1.13. Chosen R20 -> 2023-26 **1.075 < 1.102. Not adopted.**
- **Gen178, earnings-season months / lunar cycle (3 trials):** EA whole months 0.87 / 0.50 and lunar 0.57 / 0.21 both enter, but the book drops to **0.938 < 1.102** (extra equity beta). Not adopted.
- **Gen179, realized skewness XS from hourly returns (4 trials):** best L=21, n=4: 0.43 / 0.17 enters, but the book drops to **1.084 < 1.102**. Not adopted.
- **Gen180, hourly big-move continuation in Treasuries (4 trials):** all negative (best -0.38 / -0.23). The convexity flow works at the daily horizon (BC), not hourly. Rejected.
- **Gen181, dash for cash: short equities before month end (3 trials):** -0.32 / -0.77 at best. Rejected.
- **Gen182, F3 weighted to refunding months (3 trials):** flat 0.96 / 0.05, refund-weighted 0.78 / 0.33, refund-only 0.43 / 0.69. Flat kept (best on tune).
- **Gen183, oil predicts stocks (Driesprong et al. 2008; 4 trials):**
  - **Long ES/NQ/RTY/YM for the next month only after CL fell over the past 21 days: 0.47 / 0.87** (63-day version 0.32 / 1.21; long/short versions 0.10 / 0.20 and -0.11 / 0.60).
  - **Book 2023-26 1.102 -> 1.137 (2010-17 1.64, 2018-22 1.42). Adopted, 15 sleeves.**
- **Gen184 (6 trials):** copper -> stocks (long only after HG fell) 0.73 / 0.59 enters, but the book is 1.128 < 1.137 (overlaps the oil sleeve). Commodity currencies -> commodities: best -0.005 / -0.15. Not adopted.
- **Gen185, oil / copper -> Treasuries (4 trials):** best oil 0.22 / -0.62; copper 0.26 / 0.41. Rejected.
- **Gen186, oil timing in the merged bf index sleeve:** leg -0.06 / 2.28 / 0.36; bf 2.286, HOLD 1.809. **Fails the strict rule.**
- **Gen187, oil timing on BTC/ETH as a v7 sleeve:** sleeve 0.67 / 0.71 / 0.11; v7 2.472, TEST 3.381, HOLD 2.132. **Fails.**
- **Gen188, commodity MAX / idiosyncratic vol XS (4 trials):** MAX best 0.10 / 0.65; IVOL best 0.29 / 0.54 (just below the 0.3 bar). Nothing enters.
- **Gen189, short-rate (ZT) equity timing (2 trials):** best L=63 0.64 / 0.36 enters, but the book drops to **1.061 < 1.137**. Not adopted.
- **Gen190, weight caps / 1/N (walk-forward, 5 trials):** 2018-22 with 2010-17 weights: SW 0.99, CAP20 0.99, CAP12 0.98, **EQR 1.25**, EW 1.11.
  - **Chosen EQR (1/sd over sleeves with positive fit Sharpe) -> 2023-26 1.143 vs 1.137. Adopted.** The out-of-sample gain is small, but the walk-forward margin is large.
  - **Construction is now EQR (scripts/fbook.py); entrants from Gen191 are judged against 1.143.**
- **Gen191, prop sizing of the futures book (12 sizing pairs, chosen on a 2010-22 bootstrap):**
  - Chosen: **challenge 1.0 / funded 0.5 (x15% vol)**. On a 2023-26-only bootstrap: **net 2y $6.2k per 50k account** (P(profit) 0.93, p10 +$398, P(funded) 0.97).
  - Default 0.5 / 0.5: net $4.7k (P(profit) 0.96, p10 +$889).
  - More payout, slightly worse tail: the user's choice. ASSUMED firm terms.
- **Gen192, BC refinement (4 trials):** 1-day trigger on ZF/ZN/ZB (current) 0.32 is best; adding ZT 0.28; 3-day trigger 0.26 / 0.14. Current kept.
- **Gen193 (2 trials):** quarter-end USD demand -0.14 / 0.38; post-Lunar-New-Year copper -0.09 / 0.54. Rejected.
- **Gen194, Treasury butterfly mean reversion (4 trials):** gross 0.04 / -0.21, net -1.8 to -3.2 (turnover 200-365x a year). Rejected.
- **Diagnostic: NQ-only book** (validated equity sleeves on NQ only, EQR; results/nq_only_book.json):
  - 2010-17 / 2018-22 / 2023-26: 1.11 / 0.82 / 1.25, vs NQ buy-and-hold 1.11 / 0.50 / 1.23. Max DD at 10% vol about 2-4 points smaller; correlation with NQ 0.85.
  - **A single-instrument NQ book does not get near 2.0. The futures book's gains come from the diversifiers (BC, SH, F3, A3).**
- **Gen195 (2 trials):** gold autumn effect -0.49 / 0.68; yen fiscal-year-end -0.54 / -0.51. Rejected.
- **Gen196, ridge ML sleeve in bf (+ merged index sleeve):** sleeve 0.22 / 1.49 / 1.49 (CFD costs). bf 2.326 -> 2.359, HOLD 1.883 -> 2.142, but **TEST 3.698 -> 3.681 (-0.017). Fails the strict rule (near-miss).** Not adopted; the rule is not relaxed after the fact.
- **Gen197, hour-opening order imbalance (Kim and Hansen 2026; 4 trials):** best DEV 0.14 but TEST / HOLD -1.70 / -2.14 (4h: -4.1 / -4.5). Fails badly. 5-minute bars and a next-hour entry do not capture the paper's seconds-scale effect.
- **Gen198, commodity intraday momentum, first hour -> last hour (2 trials):** gross 0.24 / 0.09 / 0.19 (filtered), net -2 to -6 (hourly trades cost more than the edge). Rejected.
- **Gen199, oil -> CAD (2 trials):** -0.58 / -0.44 and -0.36 / -0.70. Rejected.
- **Gen200 (TS own-month seasonality): withdrawn before any number.** Data starts in 2010, so a 10-year history leaves almost no tuning period.

## Gen201 (2026-10-20): stand-alone index-CFD book (new account type)
- **Components** (fixed, each passed on its own): P6 vol-managed (0.49 / 1.46 / 1.04), R1 14:00 dip ensemble (1.05 / 0.56 / 1.17), calendar union (0.85 / 1.21 / 0.89). EQR weights fit 2020-22: R1 0.62, P6 0.20, CAL 0.19.
- **Book 2020-22 (fit) / 2023-24 / 2025-26: 0.97 / 1.25 / 0.99. Passes** (both unseen periods >= 0.8). By year: 1.16, 1.31, -0.15, 1.80, 0.75, 0.33, 2.06. Max DD 2023-26 at 10% vol: -11.6%. Correlation with the futures book 0.78.
- **Caveat:** the components' 2023-26 results were known from Gen147/Gen168, so only the combination is new.
- **Prop (2023-26-only bootstrap, BrightFunded 2-step $100k preset + swap-free fee):**
  - Risk 1.0 / 0.5: P(funded) 0.98, P(profit) 0.93, **net 2y $9.3k** (p10 +$1.3k).
  - Risk 1.0 / 1.0: net $15.8k (p10 +$0.8k).
  - Risk 0.5 / 0.5: net $4.2k (P(profit) 0.68).
- **Use:** a second BrightFunded (or other index-CFD) account next to bf, not inside it.
- **Gen202, futures sleeves transferred to crypto v7 (3 trials):**
  - Vol-managed long: 0.60 / 1.51 / -0.03.
  - Big-move continuation: 0.52 / 0.11 / 0.88; v7 HOLD 2.34 but TEST 3.22.
  - R1 dip: 0.77 / 0.58 / 0.21.
  - **All fail the strict rule.**
- **Gen203, equity timing sleeves (T1, T2, FC, MM, OIL) on ES+NQ instead of 4 indices (2 trials):**
  - Combined tune: ALL4 0.68, **ESNQ 0.79**.
  - **Book 2023-26 1.143 -> 1.187 (2010-17 1.54, 2018-22 1.44). Adopted.**
  - Not repeated for R1 / P1: their per-index 2023-26 results are known (Gen146), so that test would be contaminated.
- **Gen204, Santa Claus rally on ES/NQ:** 0.29 / -0.86. Does not enter.
- **Gen205, P1 IBS on ES+NQ instead of 4 indices (2 trials):** tune ALL4 0.69, **ESNQ 0.83**. **Book 2023-26 1.187 -> 1.231 (2010-17 1.54, 2018-22 1.49). Adopted.**
  - Note: the ES+NQ choice tilts the book to large-cap / tech. It was right in 2010-22 and stayed right in 2023-26, but it is a concentration risk.
- **Gen206, A3 / F3 on ZN+ZB only (4 trials):** A3 long-end 0.36 vs 0.57; F3 0.87 vs 0.96. Current kept.
- **Sanity check, EQR exposure:** the book's leverage multiplier is at its 3x cap (realised vol about 6-7%, below the 10% target). The largest sleeves (BC 21%, SH 23%, T2 10%) are about 0.1-0.3x notional on active days. No hidden over-leverage.
- **Gen207, index-CFD book R1 24h vs overnight (2 trials):** fit 0.97 vs 0.85, so the 24h version is kept (overnight would have scored 1.49 / 0.84).
- **Gen211, issuance hedging in Treasuries (2 trials):** Wed-Fri long -0.01 / -0.85; early-month short 0.17 / -0.32. Rejected.
- **Gen212, EQR static vs yearly expanding refit (walk-forward):** 2018-22 1.427 vs 1.426, so static is kept. **The fully point-in-time version scores 1.216 in 2023-26 (vs 1.231)**: the result does not depend on fitting weights through 2022.
- **Futures book now (Gen205, 15 sleeves, EQR): 2010-17 1.54 / 2018-22 1.49 / 2023-26 1.23.**
  - 2023-26: 6.9% a year at its realised vol, max DD -4.6%, 34 of 45 months positive. Years 1.65 / 0.88 / 0.88 / 1.67.
  - Prop (2023-26-only bootstrap, 50k swing, ASSUMED terms):
    - 0.5 / 0.5: P(profit) 0.98, net 2y $5.2k (p10 +$1.5k).
    - 1.0 / 0.5: P(profit) 0.94, net 2y $6.8k (p10 +$0.9k).
- **Gen213, cascade limit buys on ES/NQ (crypto transfer; 4 trials):** best 0.14 / 0.64 (2.0 sd, next-close exit). Does not enter.
- **Gen214, pension rebalancing Treasury leg:** 0.33 / -0.87, enters, but the book drops to **1.072 < 1.231**. Not adopted.
- **Gen215, K3 on ES+NQ:** tune 0.51 vs ES-only 0.56. Current kept.
- **Gen216, TFF dealer positioning in ZN/ZB (2 trials):** -0.37 / 0.22 and -0.22 / -0.43. Rejected.
- **Gen217, FOMC 3-day window in Treasuries (Hillenbrand):** 0.20 / 0.19 (2010-17 0.11, 2018-22 0.36). Positive throughout but below the 0.3 bar.
- **Diagnostic, the two largest EQR sleeves by year (2010-26):**
  - SH positive in 11 of 17 years (best 2012 1.97, worst 2014 / 2024 -0.65).
  - BC positive in 12 of 17 (worst 2012 -1.08).
  - Neither depends on a single year.
- **Gen220, dollar carry (average forward discount):** -0.15 / -0.35 (2010-17 -0.62). Rejected.
- **Gen221, sleeve-level vol targeting of F5 / G1 / A3 / U5 (walk-forward):** 2018-22 RAW 1.427 vs SVT 1.430, so SVT is chosen. **Book 2023-26 1.231 -> 1.240. Adopted by the rule, but the gain is noise-level.**
- **Gen222, grain weather premium (long Apr 15 - Jun 30):** -0.05 / -0.73. Rejected.
- **Gen223, trend sleeves without equity indices (4 trials):** G1 0.35 -> 0.28, U5 0.36 -> 0.10 on tune. Current kept.

## Gen120 run (2026-10-20): Deribit option flow (data 2020-01..2026-09, BTC + ETH)
- **D1 put-skew contrarian (primary):** 0.01 / -0.79 / -0.12; lowers v6 and bf. **Fails.**
- **D2 call-minus-put buying:** 0.35 / 0.81 / 0.05; v6 2.458 -> 2.512 but HOLD 1.90 -> 1.66; bf 2.252 -> 2.338 but HOLD 1.55 -> 1.42. **Fails** (HOLD).
- Both fail against the books they were registered against (v6 / bf), so there is no case to test against v7.

## Gen209 (2026-10-20): VIX variance risk premium / term structure (VIX data 1990-2026)
- Chosen VR2 (long ES/NQ when VRP > 0): 0.81 / 1.24. Chosen TS2 (long when VIX3M > VIX): 0.76 / 1.21. Both enter under the 0.3 bar; book 2023-26 1.240 -> 1.299, but 2010-17 / 2018-22 fall to 1.49 / 1.30.
- **Check:** VR2 is invested 84% of the time, TS2 92%; correlation with ES/NQ buy-and-hold 0.88 / 0.83. Buy-and-hold ES/NQ itself scores 0.76 / 1.17.
- **These are buy-and-hold, not timing. Overridden conservatively: NOT adopted; the book stays at 1.240.**
- The non-beta variants (VR1 36% invested: 0.51 / 0.93; TS1 8%: 0.25 / 0.22) are below buy-and-hold on tune.
- **New rule (config/rule_timing_vs_buyhold.json):** equity-timing entrants must beat buy-and-hold of their instruments on 2010-22.
- **Gen224, VIX refinements (6 trials):** F5 implied-vol sizing 0.79 vs 0.86 current; R1 x VIX 0.55 vs 0.56; VIX spike reversal 0.45 but **appraisal -0.07** (beta). No change.
- **IMPORTANT diagnostic, how much of the futures book is ES/NQ beta (Gen221 book vs ES/NQ 50/50 buy-and-hold):**
  - 2010-17: book 1.49, corr 0.71, beta-adjusted Sharpe 1.02 (buy-and-hold 1.09).
  - 2018-22: book 1.49, corr 0.76, **beta-adjusted 1.74** (buy-and-hold 0.48).
  - 2023-26: book 1.24, corr 0.79, **beta-adjusted 0.51** (buy-and-hold 1.17).
  - **Reading:** out of sample the book is mostly smarter ES/NQ exposure; its genuine excess return is about 0.5 Sharpe. It held up in the 2022 bear market (2018-22 1.49 vs buy-and-hold 0.48).
  - Per-sleeve beta-adjusted (2010-22): MM 0.52, P1 0.45, F5 0.40, R1 0.24, T2 0.17, T1 0.07, FC 0.06, OIL -0.04.
  - **Research priority: non-equity diversifiers.**
- **Gen225, Treasuries after VIX term-structure inversion (2 trials):** -0.05 / -0.54 and 0.03 / -0.81. Rejected.
- **Gen226, group risk parity (walk-forward):** 2018-22 EQR 1.43 vs **GRP 1.65**, so GRP is chosen, but 2023-26 **0.92 < 1.24** (beta-adjusted 0.35, corr 0.53). Not adopted. With one energy sleeve, SH gets 45% of the risk; the book needs more non-equity sleeves before de-betaing pays.
- **Gen227, VIX risk-off overlay on the crypto books (halve exposure when VIX > its 1-year 80th percentile, 21% of days):** v7 2.534 -> 2.483 (HOLD 2.24 -> 2.01); bf 2.326 -> 2.233. Fails. The crypto books do fine in high-VIX periods.
- **Gen228, calendar-spread momentum, 8 commodities (2 trials):** net -1.69 / -1.77 (gross 0.21-0.37 on tune, negative 2023-26; tiny spread vol means large notional and costs). Rejected.

## P1 execution correction (2026-10-20)
- P1 (IBS < 0.3) used the full-session high/low/close and filled at that same close (the optimism Gen146 found for R1).
  - Rebuilt with signal and fill at a snapshot: **16:00 ET (cash close; ES/NQ trade-at-settlement) 0.61 / 0.82 / 1.08**; 15:00 ET 0.34 / 0.08 / 1.05; book version 0.72 / 0.98 / 1.18.
- All other sleeves use information known before the fill (calendar dates, lagged signals).
- **Book corrected to P1 @16:00 ET: 1.459 / 1.451 / 1.218 (was 1.240). New reference 1.218.**
- **Live note:** P1 must be executed at the 16:00 ET settlement (TAS orders on ES/NQ; check whether the firm / micros support TAS, otherwise a market order at 15:59).
- **Gen229, auction strength (bid-to-cover surprise) continuation (2 trials):** -0.39 / -0.72 and -0.54 / -0.78. Rejected.
  - The consistent negative sign hints at reversal, but flipping it after the fact is data snooping, and there is no unused auction history to test it cleanly. Recorded only as a hypothesis.

## Gen230 (2026-10-20): prop settings for the crypto-firm books (chosen on 2022-24, evaluated on 2025-26 bootstraps)
- **v7 on HyroTrader 2-Step: 2.0 / 1.5 / stop 0.5** (challenge / funded / daily stop as a fraction of the daily limit), replacing 1.5 / 1.0 / 0.5.
  - 2025-26 net 2y: **$61.6k vs $41.6k** (p10 $33.9k vs $24.4k, P(profit) 1.00 vs 1.00).
- **bf + index sleeve on BrightFunded 2-Step swap-free: 2.0 / 1.5 / 0.5**, replacing 1.5 / 1.0 / 0.6.
  - 2025-26: **$54.5k vs $36.9k** (p10 $27.2k vs $19.0k, P(profit) 0.99 vs 0.99).
- **Stress test, mean return halved:**
  - v7: chosen $21.1k vs current $15.3k (P(profit) 0.90 vs 0.90; p10 -$0.3k vs -$0.0k).
  - bf: $18.6k vs $12.7k (0.85 vs 0.84; p10 -$3.0k vs -$2.4k).
  - The new settings stay better in mean with similar P(profit) and a slightly worse tail. **Adopted** (36 trials). Firm terms as in the presets (fees, splits, payout cadence ASSUMED where marked).
- **Gen231, index-CFD book prop settings:**
  - Chosen on 2022-24: 1.5 / 1.0. On 2025-26: net $15.2k but P(profit) 0.80, vs 1.0 / 0.5 at $8.2k and 0.91 (half-mean stress 0.69 vs 0.71).
  - **Not adopted** (Gen230 rule: P(profit) may drop by at most 0.02). The index-CFD book stays at 1.0 / 0.5; its edge is too thin for more risk.
- **Gen232, P1 long-only IBS on US100/US500 CFDs (16:00 ET) in the bf index sleeve:** leg **1.18 / 1.22 / 1.08**; bf 2.326 -> 2.350, TEST 3.719, but **HOLD 1.864 < 1.883. Fails (near-miss).**
- **Gen233, index-CFD book + P1 CFD leg:** fit 1.11, 2023-24 **1.168 < 1.247**, 2025-26 0.986 < 0.988. Fails. Gen201 stays.
- **Gen234, bf + ridge ML sleeve + P1 CFD in the index sleeve (combination of the Gen196 / Gen232 near-misses; flagged as in Gen133):**
  - **bf 2.326 -> 2.378, TEST 3.698 -> 3.699 (razor-thin), HOLD 1.883 -> 2.118; 2022 0.49 -> 0.37. Passes the strict rule; adopted.**
  - New bf = 6 crypto sleeves + ridge ML (BTC/ETH CFDs) + merged index sleeve (P6 + R1 + P1 @16:00 ET).
- **New bf (Gen234) with the Gen230 settings (2.0 / 1.5 / stop 0.5), 2025-26 bootstrap:**
  - **Net 2y $62.1k** (p10 $34.3k, P(profit) 0.998), vs old bf $54.5k with the same settings and $36.9k with the old settings.
  - Half-mean stress: $22.6k, P(profit) 0.88.
- **Diagnostic, crypto execution costs:** C* at 7.5 / 4 / 2 bp gives v7 2.534 / 2.554 / 2.565. Maker execution adds at most ~0.03; not a material lever.
  - Per-sleeve D/T/H: C* 2.03 / 2.32 / **0.60** (decayed in 2025-26), premium carry 0.87 / 0.68 / 1.15, cascade 0.40 / 1.73 / 0.79, trend 4h 0.77 / 1.43 / 0.44, Weiss 0.47 / 1.64 / 0.62, delev bounce 0.51 / 1.03 / 0.65, ridge 0.11 / 1.28 / 1.36. v7's HOLD comes from diversification.
- **Gen235, P1 overnight-only vs 24h:** tune 0.29 vs 0.68. 24h kept (unlike R1, P1's edge is not overnight).

## Gen236 (2026-10-20): firm / account choice (nested; terms partly ASSUMED, verify on the firms' sites)
- **v7:** chosen on 2022-24: **HyroTrader 2-Step $200k** (2.0 / 1.5).
  - 2025-26 net 2y **$123.5k** (p10 $68.2k, P(profit) 1.00) vs $100k account $61.6k (p10 $33.9k).
  - Half-mean stress $53.5k vs $26.4k (P(profit) 0.93 vs 0.93).
  - Fee ~$969 vs $579: one $200k account beats two $100k accounts. Losses in dollars double too.
  - Other firms on 2022-24: CFT 2-Phase 90% split $81k > HyroTrader 2-Step $100k $74k > CFT 2-Phase $73k > HyroTrader 1-Step $70k > Breakout 2-Step $55k (P 0.93).
- **bf (Gen234):** FundedNext Stellar 2-Step swap-free $64.1k vs BrightFunded Classic $62.1k (2025-26; half-mean $27.6k vs $25.8k). Marginal.
  - **Recommendation: stay with BrightFunded.** bf uses BrightFunded's crypto CFD list (40+ coins), which FundedNext may not offer; verify before switching.

## Gen237 (2026-10-20): futures account size (MFFU-type, terms ASSUMED from third-party summaries; verify incl. overnight holding)
- 2023-26 bootstrap at settings chosen on 2010-22:
  - **50k (4% EOD trailing): 1.0 / 0.5, $6.7k, P(profit) 0.95** (half-mean 0.82).
  - 100k (3%): $7.8k, 0.85 (0.65).
  - 150k (3%): $11.8k, 0.85 (0.65).
- **Several 50k accounts beat one large account** (the larger ones have a tighter percentage drawdown). Three 50k accounts: about $20k at P(profit) 0.95; they pass and fail together, every amount x3.
- **bf on a BrightFunded Classic $200k (fee ~$947 + swap-free $96, ASSUMED from a third-party listing; BrightFunded relaunched its plans in April 2026, verify):**
  - 2025-26 bootstrap net 2y **$124.4k** (p10 $68.8k, P(profit) 0.998); half-mean $45.7k (0.89).
  - About double the $100k account, as for v7.

## Gen208 / Gen210 (2026-10-20): Databento extra roots (UB, TN, NKD, PL, EMD; 2010-26)
- **Gen210:** BC + UB/TN tune 0.257 < 0.32 (current kept). Equity timing sleeves + NKD 0.696 < 0.785, appraisal 0.15 (current kept). **No change.**
- **Gen208, gold/platinum ratio -> ES/NQ (CME PL):** best SCL 0.50 / 0.83, but **appraisal -0.19** (beta). **Rejected** under the refined rule. Gen208b (Dukascopy spot) is retired: same hypothesis, already judged.

## Futures firm rule check (2026-10-20, terms checked by the user on the firms' help pages)
- **MFFU and Tradeify do NOT allow holding across the daily close** (MFFU auto-flattens at 16:10 ET; Tradeify requires flat by 16:45 ET). The futures book is a swing book.
- **scripts/futures_book_build.py** now rebuilds the whole book from its adopted settings; it reproduces the saved sleeves exactly. QPL_DAILY_FLAT=1 charges one round trip per held position per day (flat at 16:10, reopen at 18:00; the 16:10-18:00 return is ignored).
- **Daily-flat book: 0.36 / 0.72 / 0.84** (vs 1.46 / 1.45 / 1.22). Multi-market sleeves (G1, U5, A3, F3) turn negative; the ES/NQ sleeves survive (P1 0.98, OIL 0.96, R1 0.87, F5 / FC 0.73 in 2023-26).
- **Prop, 50k (2023-26 bootstrap):**
  - Swing firm: $6.7k, P(profit) 0.95 (half-mean $3.1k, 0.82).
  - Daily-flat at MFFU / Tradeify: $4.3k, 0.85 (half-mean $2.2k, 0.71).
- Swing-friendly candidates (affiliate-type sources, verify): Elite Trader Funding (Diamond Hands / Direct to Funded; "semi-automated only" may conflict), PropEd Capital (Mega Drawdown accounts), PropShop Trader (Direct swing).
- **User-checked terms:**
  - HyroTrader $200k 2-Step: $969 (refundable with the first payout), 10% / 5% targets, 5% daily, 10% max; trades on **Bybit / BloFin** (backtests use Binance perps: similar prices, funding differs slightly). A swing-drawdown upgrade (+$89) is advertised; check it.
  - BrightFunded Classic 2.0 $200k: EUR 697.90 promo (EUR 997 regular), 10% / 5%, 5% daily, 10% static, overnight / weekend allowed, swap-free add-on still listed (check it covers the bf coins).
- **Gen238, daily-flat book with the 0.3 entry bar re-applied on 2010-22:** keeps F3, P1, R1, MM; 2023-26 **0.567 < 0.835**. Not adopted.
- **Gen239, overnight return -> last half hour (intraday-flat):** ES+NQ -0.93 / -1.17 / -0.46, NQ 2010-17 -2.02 (k=0); k=0.5 also negative. **Rejected** (recent data shows reversal, not continuation).
- **Flagged analysis, R1 overnight 18:00 -> 10:00 (ES+NQ) in the daily-flat book:** sleeve 0.70 / 0.74 / 0.46; book 0.52 / 0.84 / **0.76 < 0.835**. No improvement (not adopted; the window was found on ES/NQ in Gen148 anyway).

## Gen240 / Gen241 (2026-10-20): SqueezeMetrics GEX / DIX (2011-05..2026-10)
- **Gen240, GEX-regime intraday (flat every day):**
  - Low-gamma momentum (09:30-10:00 sign held to 15:55): **0.33 / -0.22 / 0.38**, NQ 2011-17 0.12 (69 days a year).
  - Plus high-gamma reversal: 0.13 / -0.36 / -0.07.
  - **Fails** (2021-23 negative). A weak, inconsistent signal.
- **Gen241, DIX timing:** 0.51 / 1.29 but **appraisal -0.21** (invested 65%). Beta, **rejected**.
- Consequence: the exact-gamma purchase (ES options OI, ~$31) is **not** recommended; the free proxy did not show a consistent regime effect. Next: the closing-auction test (Gen242, ~$2.74 of data).

## Gen242 (2026-10-20): closing-auction imbalance, QQQ -> NQ 15:51-16:00 (Databento XNAS.ITCH imbalance, 2018-06..2026-09)
- **Median-filtered (|dollar imbalance| > 20-day median, about 125 days a year): 0.00 / 0.82 / 0.90 (2018-20 / 2021-23 / 2024-26), gross 1.02. PASSES** (the first intraday edge to pass; flat before 16:00, so it suits MFFU / Tradeify / Topstep).
- Every day: -0.32 / 0.57 / 0.07.
- **Caveat:** 2018-20 is only just above zero. **Confirmation on SPY -> ES ($25.87, ARCX.PILLAR) pre-registered as Gen243** before adoption.
- **Gen244, overnight reversal of closing pressure (against the QQQ imbalance, NQ):** from 16:00 to 09:30: 0.65 / 0.03 / 0.53; from 18:00 to 09:30: 0.45 / 0.08 / 0.38. Positive in every period, but **2021-23 is below the 0.3 bar. Fails (near-miss).**
- **Gen243, confirmation on SPY -> ES (NYSE Arca closing imbalance, same rule, no re-selection):** -1.81 / -1.38 / -0.85 (gross -0.32). **NOT confirmed.** Gen242 (QQQ) is most likely chance; the closing-auction sleeve is not adopted. (Flipping the sign would not help: gross +0.32 is below costs.)
- **Gen245, ridge-lite (Binance-only features):** sleeve 0.09 / 0.55 / 0.97 (full ridge 0.11 / 1.28 / 1.36); v6 + lite 2.425 with TEST 3.316 < 3.435. **Fails.** The Coinbase / kimchi premium, DVOL and stablecoin features carry the ridge's 2023-24 value, so live v7 needs those feeds.

## Paper traders v7 and bf2 (2026-10-20): live versions of the adopted books
- **v7** (`QPL_PAPER=v7`, `paper_v7_start.bat`, `config/paper_v7.json`): v6 + ridge ML, HyroTrader 2-Step $200k, risk 2.0, daily stop 2.5%, scale 0.881.
  - Live ridge `scripts/ridge_live.py` reproduces `results/gen108_preds.parquet` exactly (max diff 0) and gives identical weights when the data is cut at 4 moments (no look-ahead).
  - Kimchi feature (Gen105 strict): Yahoo USD/KRW dated by London day, previous day's close; reproduces `gen105_zk_strict` exactly. A Yahoo bar that is still forming is overridden by the finished (London-midnight) bar.
  - The paper code reproduces v7: **2.534 / TEST 3.493 / HOLD 2.240**. Self-test PASSED (15 cutoffs, max difference 2e-18).
- **bf2** (`QPL_PAPER=bf2`, `paper_bf2_start.bat`, `config/paper_bf2.json`): bf + ridge ML + index sleeve (P6 + R1 + P1), BrightFunded Classic $200k, risk 2.0, daily stop 2.5%, scale 0.904.
  - `scripts/index_sleeve.py` reproduces Gen234's P6 + R1 + P1 exactly; uncapped the paper code gives Gen234's **2.378 / 3.699 / 2.118**. With the real 1:5 crypto leverage cap at risk 2.0: 2.370 / 3.682 / 2.118.
  - Self-test PASSED, including cutoffs around the 14:00 / 16:00 ET index entries.
- New live feeds (run on the user's PC): `src/qpl/live/ml_feeds.py` (Upbit, USD/KRW, Deribit DVOL; DVOL tested from the cloud: it replaces the research file's still-forming last bar) and `src/qpl/live/index_feed.py` (Dukascopy hour candles + same-day hourly tick files; not testable from the cloud because of throttling).
- Note: the bf2 index CFDs carry swap at BrightFunded (US100 long -910 points per lot per day in the MT5 export); the backtest assumes the swap-free add-on. **Verify that swap-free covers the index CFDs**, or the P6 overnight long pays swap.

## Gen246 (2026-10-20): cross-asset ridge and international P6 (2 trials, `config/gen246_protocol.json`)
- **A, ridge+ (Gen108 ridge + VIX daily change + US500 day return):** sleeve perp 0.04 / 1.11 / 1.57 (full ridge 0.13 / 1.28 / 1.36); v7 2.534 -> 2.538, HOLD 2.24 -> 2.30, but **TEST 3.494 -> 3.446**. bf2 2.378 -> 2.355. **Fails** (strict rule; DEV 0.04 also weak). The cross-asset inputs shift ridge value from 2023-24 to 2025-26 without adding to it overall.
- **B, P6 on DE40 / UK100 / JP225 in bf2:** leg -0.25 / 1.20 / 1.10; bf2 2.378 -> 2.361 (TEST 3.699 -> 3.622). **Fails** (negative DEV 2020-22, like Gen175's international R1).
- Status: the adopted books (v7, bf2) are unchanged.

## Gen249 (2026-10-20): USDT premium, ETH-BTC premium spread, Weiss every Friday (3 trials, `config/gen249_protocol.json`)
- **A, USDT premium (Coinbase USDT-USD, z > 1 -> long BTC/ETH):** sleeve 0.98 / 1.81 / 1.14 (DEV from 2021-06), corr C* 0.07. Strong alone, but v7 2.534 -> 2.534 with TEST 3.494 -> 3.359; bf2 2.378 -> 2.282. **Fails the strict rule** (redundant with what the books already hold, most likely the ridge's Coinbase-premium feature).
- **B, ETH-BTC Coinbase premium spread (market-neutral):** 1.32 / -0.24 / -0.26. **Fails.**
- **C, Weiss reversal on every Friday (replacing last-Friday-only):** every-Friday sleeve -0.17 / 1.53 / -0.40 vs last-Friday 0.47 / 1.64 / 0.62; v7 2.421, bf2 2.314. **Fails** (weekly expiries carry no edge; the monthly effect stays).
- **Gen250, ridge + USDT premium feature:** sleeve -0.15 / 1.32 / 1.35; v7 2.527 (< 2.534), bf2 2.360. **Fails.** The USDT premium's information is already in the books.
- **Gen251 A, ridge 3-day horizon with overlapping holds:** sleeve 0.02 / 1.91 / 1.00; v7 2.463 (HOLD 1.98). **Fails.**
- **Gen251 B, ridge alpha bag (1/10/100):** v7 2.536 / 3.496 / 2.237, bf2 2.377: the same model in effect. **Fails the strict rule (HOLD -0.003); no change.**
- **Gen252, swap-free TSMOM on 12 FX / metals / energy CFDs (21/63/252-day sign blend, 10% vol):** 2014-19 0.13, then 0.06 / -0.35 / 0.17; corr with bf2 -0.10; bf2 2.378 -> 2.260. **Fails.** Even without swap, FX/commodity trend has had too little return since 2020 to help.

## Gen253 (2026-10-20): six crypto cross-section / flow ideas (6 trials, `config/gen253_protocol.json`, `scripts/gen253_xs.py`)
| Idea | sleeve D / T / H | corr C* | v7 2022-26 [2022, TEST, HOLD] | result |
|---|---|---|---|---|
| A volume shock | 0.39 / 1.18 / 0.16 | 0.13 | 2.505 | fails |
| B residual momentum | 1.16 / 0.70 / 0.08 | 0.07 | 2.566 [1.54, 3.42, 2.31] | fails (TEST down) |
| C near 90-day high | 1.57 / -0.04 / 0.30 | -0.09 | 2.642 [1.78, 3.34, 2.43] | fails (TEST down) |
| **D betting against beta** | **1.44 / 1.49 / 0.57** | 0.25 | **2.704 [1.61, 3.73, 2.19]** | **near miss: sleeve passes its bars, book +0.17 and TEST up, but HOLD 2.190 < 2.240. Fails the strict rule.** |
| E BTC-alt rotation | 1.11 / -0.60 / -0.49 | 0.05 | 2.379 | fails |
| F pump fade | -0.65 / -3.02 / -1.76 | -0.42 | 1.865 | fails badly (pumps continue) |
- Not done on purpose: combining C and D (their TEST / HOLD weaknesses offset) would be selection on the judging windows.

## Gen254 / Gen255 (2026-10-20): four more crypto XS ideas, then two post-hoc sign reversals (6 trials)
- **Gen254:** OI growth (low long) -0.62 / -0.66 / -0.99; taker-imbalance momentum 1.79 / 0.58 / 0.34 (v7 2.619 but TEST 3.39); Amihud illiquidity 2.00 / 0.15 / -0.57; top-trader ratio change -1.20 / -0.61 / -0.57. All fail.
- **Gen255 (sign reversals, registered after seeing Gen254, with extra bars):** reversed OI growth -0.10 / -0.39 / -0.16 and **-3.00 (2022) / -0.72 (2023-26) on the 40 untouched coins**; reversed top-trader change 0.78 / -0.68 / -1.18. Both fail: the Gen254 negatives were costs, not a reversed edge.
- **Gen256, vol-managed long BTC/ETH (P6 rule on crypto):** v7 sleeve 0.58 / 1.53 / 0.00 (corr C* 0.54), v7 2.291; bf2 sleeve 0.82 / 1.74 / 0.09, bf2 2.116. **Fails** (crypto beta is already in the books through C*; no edge in 2025-26).
- **Gen257, betting-against-beta in bf2 + replication:** bf2 sleeve 1.69 / 0.59 / 0.57, bf2 2.378 -> 2.326 (HOLD 1.994). **On the 40 untouched extra coins: 2020-21 2.01, 2022 -1.86, 2023-26 -0.38.** Fails; the Gen253 v7 near miss does not replicate, so it was most likely luck. The strict rule did its job.
- **Session tally (Gen246-257): 21 pre-registered trials on existing data, none passes.**
- **Gen258 A, ridge + market breadth features (breadth, mean funding, total OI change, dispersion):** v7 2.427, bf2 2.296. **Fails.**
- **Gen258 B, recency-weighted ridge (half-life 365 days):** v7 2.490 [1.38, 3.56, 2.06], bf2 2.325. **Fails** (HOLD lower).
- **Session tally (Gen246-258): 23 pre-registered trials on existing data, none passes.**

## Gen259 (2026-10-20): four new strategy types (4 trials, `config/gen259_protocol.json`, `scripts/gen259_newtypes.py`)
| Idea | v7 sleeve D / T / H | v7 | bf2 sleeve | bf2 | result |
|---|---|---|---|---|---|
| A PCA stat-arb (Avellaneda-Lee, 20 perps) | -0.76 / -0.62 / -0.45 | 2.187 | - | - | fails |
| B funding time-series carry (BTC/ETH) | -0.11 / -0.09 / 0.75 | 2.408 | -0.30 / -0.24 / 0.75 | 2.307 | fails |
| C NR7 breakout (BTC/ETH, 5-minute fills) | 1.73 / -0.40 / -0.33 | 2.370 | 1.83 / -0.22 / -0.13 | 2.320 | fails (edge gone after 2022) |
| D Asian-range breakout (BTC/ETH) | 0.85 / -0.23 / 1.51 | 2.326 | 1.11 / 0.19 / 1.91 | 2.278 | fails (TEST) |
- **Session tally (Gen246-259): 27 pre-registered trials on existing data, none passes.**
- **Gen260, session-range breakouts on index CFDs (5-minute, 2018+):** DE40 30-minute opening range 2018-19 -0.76, then 0.50 / -1.42 / 0.13, bf2 2.263; US500+US30 pre-market range 0.10, then 0.12 / -0.12 / -0.43, bf2 2.180. **Both fail.**
- **Session tally (Gen246-260): 29 pre-registered trials on existing data, none passes.**

## Gen247 / Gen248 (2026-10-21): new data from the user's PC (Upbit altcoins, Binance spot taker flow, trade-size flow; 5 trials)
- **Gen247 A, Korean (kimchi) premium on 16 altcoins (z > 1 long 0.1, z < -1 short 0.1, perps): PASSES v7.**
  - Sleeve 0.25 / 1.24 / 0.77, corr C* -0.04. **v7 2.534 -> 2.547; TEST 3.494 -> 3.708, HOLD 2.240 -> 2.345** (2022 1.38 -> 0.99).
  - Checks (`results/gen247_check.json`, descriptive): 15 of 16 coins positive; 30-day block placebo p = 0.01 (actual 0.66 vs placebo mean -0.16, p95 0.39); z > 0.75 also passes (2.571), z > 1.25 2.509; entry 1 day late, FX lagged 2 days and 2x costs keep TEST / HOLD positive.
  - **ADOPTED: v8 = v7 + altcoin kimchi.** In bf2 (CFD altcoins only) 2.373 < 2.378: not adopted there.
- **Gen247 B, ridge + Binance spot taker imbalance features:** v7 2.539 but TEST 3.492 < 3.494 (fails); **bf2 2.378 -> 2.383, TEST 3.702, HOLD 2.125: passes the strict rule. Adopted for bf2 by the rule; the gain is noise-level (+0.005).**
- **Gen247 C, spot-led XS:** -0.17 / 0.01 / 0.74. Fails.
- **Gen248 A, whale-minus-retail taker flow sleeve:** 0.66 / 1.03 / -0.00. Fails. **Gen248 B, ridge + trade-size features:** v7 2.545 / HOLD 2.182, bf2 2.384 / HOLD 2.080. Fails.
- **Reference from here: v8 2.547 / 3.708 / 2.345 (v7 + altcoin kimchi); bf2 2.383 / 3.702 / 2.125 (spot-flow ridge).**
- **Gen261 (vs v8, 2 trials):** Upbit attention share XS -0.37 / 1.20 / -0.83; spot-vs-perp volume dominance XS 0.20 / 1.54 / -1.71. **Both fail** (strong 2023-24, negative 2025-26).
- **Gen263, pooled altcoin ridge with kimchi / Coinbase / spot-flow features (vs v8):** -0.01 / 1.21 / -0.55, v8 -> 2.227. **Fails** (like Gen110: the altcoin ML does not hold in 2025-26; the simple kimchi rule does).
- **v8 vs v7, HyroTrader 2-Step $200k at 2.0 / 1.5 (bootstrap, same method as Gen236; descriptive):** 2025-26 mean net $123.5k -> **$133.1k** (p10 $68.2k -> $61.2k, P(profit) 1.00 -> 0.998); 2023-26 $168.6k -> **$177.1k** (p10 $100.5k -> $107.1k). Backtest-based, so optimistic in level; the difference is what matters.
- **Paper trader v8** (`QPL_PAPER=v8`, `paper_v8_start.bat`, `config/paper_v8.json`, scale 0.882): reproduces 2.547 / 3.708 / 2.345 on the research pack.

## Gen264 (2026-10-21): kimchi refinements from the user's papers (2 trials, vs v8)
- Papers read: Makarov & Schoar 2020 (JFE), Choi, Lehar & Stauffer 2022, Eom 2021 (FRL), Lee & Oh 2022, Koch & Dimpfl 2022.
- **A, idiosyncratic altcoin premium (alt kimchi minus BTC kimchi, Makarov-Schoar), market-neutral XS:** -0.89 / -0.06 / -1.21. **Fails.** The tradable information is in the total premium (Gen247), not the coin-specific part.
- **B, kimchi bubble reversal (kimchi z > 1 and Korean volume-share surge -> short, Eom):** -1.07 / -1.43 / 0.25. **Fails**: "bubbles" keep running, consistent with v8's momentum use of the premium.
- Not testable here: Lee & Oh (confidential remittance data); Koch & Dimpfl (Google / Twitter attention, not available; the volume-share proxy failed in Gen261).
- **Gen266, hourly Upbit -> Binance lead-lag (premium jump > 3 sd -> follow for 4 h, 18 coins):** 1.05 / -1.34 / -1.31, v8 -> 2.030. **Fails**: the lead existed in 2020-22 and has been arbitraged away since; only the slower daily premium signal (Gen247) survives.
- **Gen267, the v8 altcoin-kimchi sleeve in bf2 on all 16 BrightFunded altcoins (10 bp + 1.2 bp, swap-free):** sleeve 0.11 / 1.07 / 0.60; bf2 2.383 -> 2.366 with **TEST 3.702 -> 3.869, HOLD 2.125 -> 2.162** but 2022 0.37 -> 0.08. **Fails the strict rule (overall lower).** Same pattern as in v8 (helps 2023-26, hurts 2022); not adopted for bf2.
- **Gen268, ridge + Korean risk-appetite breadth (mean altcoin kimchi z):** v8 2.547 -> **2.554** [1.00, 3.709, 2.353]: **passes the strict rule (noise-level, +0.007); research reference v8.1.** Not pushed to the running v8 paper trader (a restart for +0.007 costs more than it gains); it is cheap to add at the next restart (the feature comes from the alt-kimchi z's v8 already computes). bf2: 2.377 < 2.383, fails.
- **Reference from here: v8.1 2.554 / 3.709 / 2.353** (v8 + Gen268 ridge).
- **Gen269, altcoin demand composite (mean of kimchi z and Coinbase premium z per altcoin, replacing the alt-kimchi sleeve):** 0.37 / 1.03 / 0.37; v8.1 -> 2.401. **Fails**: for altcoins the Korean premium carries the signal and the Coinbase premium adds noise (consistent with Gen102's failed Coinbase altcoin premium).

## Gen265 (2026-10-21): Google search attention (user download, 7 terms 2020-26; 2 trials vs v8.1)
- **A, attention momentum ('bitcoin' interest 7d vs 30d, z > 1 -> long BTC/ETH):** 0.41 / 1.14 / -0.46; v8.1 -> 2.416. **Fails** (2-day-delay version similar: 0.51 / 0.95 / -0.57).
- **B, halve the book the day after an attention spike (> 2 sd, 185 days):** 2.403 [0.77, 3.64, 2.13]. **Fails**: spikes often come before rebounds, so de-risking cuts good days (2022 1.00 -> 0.77).
- **BrightFunded commission (support answer, 2026-10-21, user-verified):** crypto 0.012% per side (= the 1.2 bp in bf2), indices $0, FX $3 / lot, commodities 0.001% of volume; same in Challenge and Funded. bf2's cost model is confirmed. **Swap-free add-on: support confirms it "eliminates all swap fees"** (all instruments, incl. index and crypto CFDs). bf2's no-swap assumption is confirmed; buy the add-on with the challenge.

## bf2 cost reality check (2026-10-21, BrightFunded MT5 export: median of 10 spread samples, weekday 11:30 NL; descriptive)
- Measured spreads (bp): BTC 0.36, ETH 6.2, SOL 3.7, XRP 3.1, LINK 3.2, LTC 4.9, ADA 8.9, AVAX 12.3, DOGE (XDG) 21.9, BCH 34.8, DOT 43.2; US100 0.31, US500 0.66, US30 0.19 (bf2 assumes BTC 0.4, ETH 2.7, altcoins 10, indices 1 bp). Swaps on the exported (non-swap-free) account are non-zero, as expected.
- **bf2 with measured spreads: whole spread per side (pessimistic) 2.286 [0.31, 3.61, 2.01]; half spread per side (realistic) 2.427 [0.41, 3.75, 2.17]; model 2.383.** The cost model is fair: real costs land between the two.
- Cost cap (drop DOT and BCH, spreads > 25 bp; half-spread costs): 2.361 (HOLD 1.95). **Not applied**: their trades are rare and still pay.
- **Gen270, altcoin kimchi in bf2 at measured costs (14 altcoins; ATOM, TRX excluded on cost):** sleeve 0.12 / 1.15 / 0.65; bf2 2.427 -> 2.423 with **TEST 3.751 -> 3.939, HOLD 2.169 -> 2.219**, 2022 0.41 -> 0.13. **Fails by 0.004 overall.** Third time the same pattern (Gen247 bf2, Gen267, Gen270): the signal helps 2023-26 clearly and hurts 2022; the strict rule is not relaxed.
- **bf2 research reference from here: measured costs (half spread per side), 2.427 / 0.408 / 3.751 / 2.169** (`QPL_COSTS=model` restores the old one).
- **Gen271, cheap BrightFunded CFDs added to the bf2 universe (measured costs; reference reproduced 2.427):** + BNB 2.408 [0.50, 3.77, 2.03]; + BNB, UNI, NEAR, AAVE 2.301. **Both fail** (HOLD lower); the bf2 universe stays at 11 coins.
- **Gen272, intraday periodicity (Gen154 rule) on US100/US500/US30 CFDs at BrightFunded costs (full measured spread per side, 0 commission; 9-setting grid on 2018-22, CFD data starts 2018):** every setting negative (-0.97 to -2.66). **Fails**: the futures periodicity signal does not carry over to the CFDs even at near-zero costs.
- Cost note: bf2's index sleeve at a realistic 0.3 bp per side (measured US index spreads 0.19-0.66 bp, zero commission) instead of 1 bp: bf2 2.427 -> 2.435 [0.42, 3.76, 2.18]. The 1 bp assumption is kept as a safety margin.

## Gen273 (2026-10-21): CME asset-manager positioning; stablecoin dominance (2 trials vs v8.1)
- **A, CFTC TFF asset-manager net long change (CME BTC / ETH, weekly, from the Monday after release):** -0.17 / 0.42 / 0.26; v8.1 -> 2.524. **Fails** (with Gen119's leveraged funds, CME positioning carries no usable signal).
- **B, stablecoin dominance (USDT+USDC vs BTC+ETH caps, 30-day change, risk-off when rising):** 0.23 / 0.63 / 0.04 (caps to 2026-05); v8.1 -> 2.340. **Fails.**
- **Gen274 A, average trade size XS (20 perps, rising trade size long):** 1.29 / -0.34 / 0.52; v8.1 -> 2.456. **Fails.** **Gen274 B, altcoin OI share rotation:** -0.44 / -0.53 / -0.97. **Fails.**
- **Gen275, Gen105 demand composite (Coinbase + Korean premium, BTC/ETH):** sleeve 1.17 / 1.29 / 1.06 (corr C* 0.04), but **A** added to v8.1: 2.437 (TEST 3.45); **B** replacing bf2's Coinbase-premium sleeve: 2.314 (2022 0.14). **Both fail**: redundant with the ridge, which already holds zc and zk.
- **Gen276, v8.1 with the composite INSTEAD of the ridge:** **2.601** [1.62, 3.55, 2.19] vs 2.554 [1.00, 3.71, 2.35]. **Fails the strict rule** (TEST and HOLD lower; the overall gain comes from 2022). The ridge stays. Note: simpler (no DVOL / stablecoin / refit) at almost the same level, a fallback if the ridge's live feeds ever break.

## Gen262 (2026-10-21): broader and regional demand premia (user download flow data 3; 3 trials vs v8)
- **A, the Gen247 altcoin kimchi rule on 28 extra Upbit-listed coins (untouched by Gen247):** sleeve **0.19 / 1.07 / 0.57** (positive in every period, passes its own bars, corr C* -0.07), but v8 2.547 -> 2.408 (2022 and HOLD lower; overlaps the existing alt-kimchi sleeve). **Fails as an addition, but it is an out-of-sample replication of the v8 edge on new coins.**
- **B, Turkish + Brazilian USDT premium (Binance USDT/TRY, USDT/BRL vs FX):** -0.06 / 0.84 / 0.26; v8 2.402. **Fails.**
- **C, Turkish + Brazilian BTC premium:** -0.08 / 0.84 / 0.24; v8 2.400. **Fails.** Korea's premium is special (capital controls, Makarov-Schoar); other regions add nothing.
- **Gen278, one alt-kimchi sleeve over 44 coins (16 + 28 extras, same total size; extras at 10 bp):** sleeve 0.19 / 1.08 / 0.57 vs the 16-coin 0.25 / 1.24 / 0.77; v8.1 2.554 -> 2.547 (HOLD 2.28). **Fails**: the extra coins carry the signal more weakly (smaller, noisier coins); the 16-coin sleeve stays.

## Gen279 (2026-10-21): Bitfinex margin positions ("Bitfinex whales"; new data, public API from the cloud, hourly 2021-02+; 2 trials vs v8.1)
- **A, follow whale long changes (7-day change of margin longs, z > 1 long):** 0.05 / -0.49 / -0.78; v8.1 -> 2.209. **Fails.**
- **B, follow the long/short ratio:** -0.03 / 0.69 / -1.17; v8.1 -> 2.403. **Fails.** Not reversed after the fact (Gen255 lesson).
- **Gen280, continuous alt-kimchi sizing (0.1 x clip(z/2)) instead of the threshold:** sleeve 0.26 / 0.97 / 0.75 vs threshold 0.25 / 1.24 / 0.77; v8.1 -> 2.520. **Fails**: the edge sits in the strong-signal days; small z's add noise.
- **Gen281, CME futures basis level (annualised, vs Coinbase spot; z > 1 long BTC / ETH):** 0.48 / -0.00 / 1.57 (BTC median basis 6.5% a year); v8.1 -> 2.570 [1.33, 3.35, 2.47]. **Fails** (TEST lower). Watchlist: strong in 2025-26 (ETF era), nothing in 2023-24.
- **Gen282, euro-area premium (Binance BTC/EUR, ETH/EUR vs EUR/USD):** -0.35 / 0.08 / -0.33; v8.1 -> 2.395. **Fails.** With Gen262 B/C: among regional premia only Korea's carries a signal.
- **Gen283, short after Upbit listing (31 events 2020-26, Binance perp short 0.1 for 30 days from the day-1 close):** sleeve **-0.49 / -0.03 / 0.76** (corr C* -0.24); 21 of 28 coins fell over the 30 days (median about -6%), but 2021 bull-market winners (NEAR +97%, SOL +50%) sink DEV. **Book v8.1 2.554 -> 2.720 [1.17, 3.85, 2.45] - every period up - but the sleeve fails its own DEV / TEST bars (the book gain is a hedge effect, not standalone profit). Fails the rule; watchlist** (few events; revisit as listings accumulate).
- **Gen284, Korean-session premium change (00:00 -> 09:00 UTC) -> trade the rest of the day, 18 coins:** -0.62 / -0.33 / 0.31; v8.1 -> 2.518. **Fails**: like Gen266, intraday Korean moves do not carry over; only the slow daily premium (Gen247) does.
- **Gen285, weekly altcoin kimchi (7-day mean premium, weekly rebalance) replacing the daily sleeve:** sleeve 0.11 / 0.97 / 0.66; v8.1 2.554 -> **2.618** [1.28, 3.78, 2.10]. **Fails the strict rule (HOLD lower)**; the daily version stays.
- **Gen286, strategy momentum (sleeve at half weight while its trailing 90-day P&L is negative; 40% of sleeve-days):** v8.1 2.554 -> 2.341 [0.43, 3.65, 2.09]. **Fails**: crypto sleeve P&L mean-reverts over 90 days rather than trending; with Gen113, performance-based reweighting does not help.
- **Gen287, liquidation-flush bounce from Kraken Futures liquidation volume (new data, public analytics, 2022-03+; 33 signal days):** -0.90 / -0.08 / 0.31; v8.1 2.552. **Fails** (Kraken is a small venue; forced flows are already covered by the cascade / deleveraging-bounce sleeves). Kraken also publishes order-book depth / liquidity / long-short / top-trader history, but only from 2023-05 (no DEV period under our rules) - revisit when a pre-2023 source exists.

## Gen288 (2026-10-21): ridge trained on volatility-scaled targets - ADOPTED (v8.2)
- **Change:** the ridge's training target is next-day return / 30-day vol (instead of the raw return); everything else unchanged.
- **v8.1 2.554 [1.00, 3.709, 2.353] -> v8.2 2.636 [1.20, 3.764, 2.357]: passes the strict rule (every period up).** Ridge sleeve 0.16 / 1.65 / 1.55 (was about 0.06 / 1.30 / 1.38). In bf2: 2.406 < 2.427, not adopted there.
- Checks (`results/gen288_check.json`, descriptive): without kimchi breadth 2.635; 7-day vol scaling 2.657; ridge alpha 3 / 30: 2.637 / 2.636; **2x costs 2.574** (still above v8.1); **entry 1 day late 2.360** (HOLD 1.71): the signal lives about one day, so it must be traded on time (the paper trader does, at 00:00 UTC).
- **Reference from here: v8.2 2.636 / 3.764 / 2.357.**
- **v8.2 vs v8, HyroTrader 2-Step $200k at 2.0 / 1.5 (bootstrap, descriptive):** 2025-26 mean net $133.1k -> **$138.7k** (p10 $61.2k -> **$68.9k**); 2023-26 $177.1k -> **$181.4k** (p10 $107.1k -> $109.7k). Better on both the average and the unlucky tail.
- Paper trader v8.2 was built and self-tested, then superseded by v8.3 before it was started (files removed).
- **Gen289 (vs v8.2), inverse-vol position sizing:** A ridge 2.652 [1.20, 3.761, 2.344]; B alt kimchi 2.627 [1.23, 3.75, 2.31]. **Both fail** (TEST / HOLD a hair lower).
- **Gen290, v8.2 ridge trained on 18 coins (BTC, ETH + 16 altcoins), traded on BTC / ETH:** sleeve -0.42 / 1.26 / 1.29; v8.2 -> 2.445. **Fails**: altcoin rows add noise to the BTC / ETH model (consistent with Gen110 / Gen263).
- **Gen291 (vs v8.2):** A Huber regression instead of ridge 2.553; B raw + vol-scaled ridge ensemble 2.603 [1.11, 3.75, 2.37]. **Both fail**; the v8.2 ridge stays.
- **Gen290 / Gen291** see above. 

## Gen292 (2026-10-21): premium carry with inverse-volatility weights inside each leg - ADOPTED (v8.3)
- **v8.2 2.636 [1.20, 3.764, 2.357] -> v8.3 2.700 [1.29, 3.828, 2.376]: passes the strict rule (every period up).** bf2: 2.427 -> 2.437 [0.38, 3.752, 2.214] passes too, but noise-level; research reference only (the running bf2 paper trader is not restarted for it).
- Checks (`results/gen292_check.json`, descriptive): 60-day vol 2.691; weight cap 2x equal 2.698; 2x costs 2.655 (above v8.2); 14-day vol 2.630 (weaker). Equal weights (current) 2.636.
- **Reference from here: v8.3 2.700 / 1.293 / 3.828 / 2.376.**
- v8.3 vs v8, HyroTrader 2-Step $200k at 2.0 / 1.5 (bootstrap, descriptive): 2025-26 mean net $133.1k -> **$137.7k** (p10 $61.2k -> **$70.6k**); 2023-26 $177.1k -> **$183.1k**.
- **Paper trader v8.3** (`QPL_PAPER=v83`, `paper_v83_start.bat`, `config/paper_v83.json`, scale 0.886): reproduces 2.700 / 1.293 / 3.828 / 2.376; self-test PASSED (no look-ahead).
- **Gen293 (vs v8.3), inverse-vol sizing:** A cascade 2.681 [1.21, 3.891, 2.323]; B deleveraging bounce 2.659 [1.33, 3.779, 2.285]. **Both fail** (one period lower each).
- **Gen294, pooled altcoin ridge with volatility-scaled targets (Gen263 rerun):** -0.02 / 1.26 / 0.06, corr C* 0.39; v8.3 -> 2.467. **Fails** (altcoin ML stays unstable in 2025-26, whatever the target).
- **Gen295, bf2 with the v8.3 ridge (kimchi breadth + vol-scaled target, no spot features):** ridge sleeve 0.28 / 1.87 / 1.68 but bf2 2.401 [0.37, 3.72, 2.16]. **Fails**; bf2 keeps its spot-flow ridge.
- **Gen296, inverse-vol sizing across US100 / US500 / US30 inside bf2's R1 / P1 legs:** 2.425 [0.42, 3.74, 2.17] vs 2.427. **Fails** (no effect).
- **Gen297, v8.3 ridge with volatility-normalised return features:** 2.704 [1.37, 3.915, 2.218]. **Fails the strict rule (HOLD lower)**; watchlist.
- **Gen298, deleveraging bounce with an OI-drop z-score trigger (< -2.5 sd):** 39 signals vs 98 episodes for the -10% rule; v8.3 -> 2.601 [0.94, 3.83, 2.13]. **Fails**; the fixed -10% trigger stays.
- **Round tally (Gen293-298, vs v8.3 / bf2): 6 pre-registered trials, none passes; Gen297 (vol-normalised ridge features, 2.704) to the watchlist.**
- **Gen299, nested parameter tuning (each setting picked on 2020-22 only: alt-kimchi threshold 0.75, premium-carry window 3, ridge alpha 3; 12 trials):** 2.574 [1.24, 3.66, 2.20] vs v8.3 2.700. **Fails**; the DEV-optimal settings do not carry forward, so the v8.3 parameters stay.
- **Gen300 (vs v8.3), ridge + one new feature family each:** A variance risk premium (DVOL minus 30-day realised vol, + 7-day change): ridge sleeve 0.48 / 1.90 / 1.39, book **2.746** [1.45, 3.878, 2.344]; **fails (HOLD lower)**, watchlist. B Korean breadth change: 2.675, fails. C weekend / Monday dummies: 2.711 [1.20, 3.841, 2.466] with TEST and HOLD up, but the sleeve's DEV is -0.07: **fails the sleeve bar**, watchlist.

## Gen301 (2026-10-21): bf2 ridge + variance risk premium - ADOPTED (bf2.1)
- **A, bf2's spot-flow ridge + VRP features (DVOL daily vol minus 30-day realised vol, and its 7-day change):** ridge sleeve 0.65 / 1.81 / 1.48 (old 0.4-ish DEV); **bf2 2.427 -> 2.464 [0.514, 3.804, 2.182]: every period up, passes the strict rule. Adopted: bf2.1.**
- **B, bf2's ridge + weekend / Monday dummies:** sleeve 0.10 / 1.55 / 1.70; bf2 2.462 [0.381, 3.771, 2.240]: passes too, but lower book Sharpe (protocol: the higher one is adopted; a combination needs its own trial).
- Honest caveat: in v8.3 the same VRP features gave 2.746 but HOLD 2.344 < 2.376 (Gen300 A, fail). Two passing bf2 trials out of five ridge-feature trials today; the gain is +0.04, small against noise.
- **Reference after Gen301: bf2.1 2.464 / 0.514 / 3.804 / 2.182** (paper version folded into bf2.2 below before it started).

## Gen302 (2026-10-21): bf2.1 + calendar - ADOPTED (bf2.2); ETH-BTC relative-value ridge fails (3 trials)
- **A, bf2.1 ridge + weekend / Monday dummies (Gen301 A + B combined, its own trial):** ridge sleeve 0.51 / 1.86 / 1.67; **bf2.1 2.464 -> 2.501 [0.523, 3.812, 2.247]: every period up, passes. Adopted: bf2.2.**
- **B, ETH-minus-BTC relative-value ridge (market neutral) in v8.3:** -0.45 / -0.43 / -0.21; v8.3 -> 2.453. **Fails.** **C, the same in bf2.1:** -0.34 / -0.11 / 0.15; 2.345. **Fails**: the features predict direction, not the ETH-BTC spread.
- Paper version `bf22` (scripts/paper_v5.py, config/paper_bf22.json, scale 0.902): spot-flow + VRP + calendar ridge (scripts/ridge_live.py spot / vrp / cal), measured BrightFunded spreads (cfd_book.measured_costs), live Binance spot BTC/ETH feed (src/qpl/live/ml_feeds.py spot). With the 1:5 crypto cap at risk 2.0: 2.496 / 0.523 / 3.800 / 2.247.
- **bf2 line: 2.427 (measured costs) -> bf2.1 2.464 -> bf2.2 2.501.** Reference from here: **bf2.2 2.501 / 0.523 / 3.812 / 2.247.**

## Gen303 (2026-10-21): v8.3 ridge + the bf2.2 features - ADOPTED (v8.4)
- **A, v8.3 ridge + VRP + weekend / Monday dummies:** ridge sleeve 0.27 / 1.91 / 1.55; v8.3 -> **2.748** [1.330, 3.882, 2.427]: passes.
- **B, A + Binance spot taker flow (simb, sdiv):** sleeve 0.28 / 1.94 / 1.54; v8.3 -> **2.750 [1.324, 3.896, 2.428]: passes. Adopted (higher book Sharpe, the standing rule): v8.4.** A and B differ by noise; B uses the same live spot feed as bf2.2.
- Same pattern in both books: VRP alone or calendar alone fell short on one period in v8.3, the combination lifts every period in both v8.3 and bf2. Caveat: 7 ridge-feature trials today (Gen300 3, Gen301 2, Gen303 2), 4 pass; selection among them is part of the count.
- Paper version `v84` (config/paper_v84.json, scale 0.895): reproduces 2.750 / 1.324 / 3.895 / 2.428 on the research pack. **Self-tests PASSED for v84 and bf22** (no look-ahead, frozen hours equal the final recomputation).
- **v line: v8.3 2.700 -> v8.4 2.750.** Reference from here: **v8.4 2.750 / 1.324 / 3.896 / 2.428.**
- **Gen304 (6 trials, ridge features in v8.4 / bf2.2):** A positioning (top-trader and all-account long/short ratios): v8.4 **2.815** [1.68, 3.94, 2.284], bf2.2 2.521 [0.74, 3.82, 2.142]; both **fail (HOLD lower)**, watchlist. B realised skewness / downside variance share: 2.718 / 2.486, fail. C US500 previous-day return + vol: 2.718 / 2.495 [0.57, 3.76, 2.26], fail.
- **Gen305 (4 trials, ridge estimation):** A weekly refit: v8.4 2.709, bf2.2 2.486; B alpha ensemble (3/10/30/100): v8.4 2.747, bf2.2 2.500. **All fail**; the monthly alpha-10 ridge stays (the ensemble is practically identical).

## Gen306 (2026-10-21, 4 trials): altcoin kimchi in the CFD book - ADOPTED (bf2.3)
- **A, bf2.2 ridge + kimchi breadth:** 2.491. **B, bf2.2 ridge with the vol-scaled target:** 2.465. **Both fail.**
- **C, bf2.2 + the Gen270 alt kimchi sleeve (14 altcoin CFDs, measured spreads):** sleeve 0.12 / 1.15 / 0.65; **bf2.2 2.501 -> 2.506 [0.313, 3.985, 2.298]: TEST +0.17, HOLD +0.05, passes. Adopted: bf2.3.** The full-period gain is noise-level (2022 falls 0.52 -> 0.31; the rule judges TEST and HOLD); the same sleeve already runs in v8 since Gen247.
- **D, the v8.4 ridge forecast applied to an altcoin basket:** sleeve 0.49 / 1.84 / 0.65 but corr C* 0.32 > 0.3; v8.4 -> 2.554. **Fails.**
- Paper version `bf23` (**self-test PASSED**; config/paper_bf23.json, scale 0.893; alt sleeve in scripts/paper_v5.py compute_bf, cfd_book.ALT_CFD): with the 1:5 cap at risk 2.0 2.502 / 0.313 / 3.977 / 2.298. Harness reference (bf2lab QPL_BF_REF) now bf2.3.
- **Reference from here: bf2.3 2.506 / 0.313 / 3.985 / 2.298.**
- **Gen307, v8.4 + the Coinbase premium sleeve on perps (the bf rule):** sleeve 0.73 / 1.30 / 0.66, corr C* -0.04; v8.4 -> 2.668 [1.44, 3.80, 2.25]. **Fails**: with the Coinbase z inside the ridge the separate sleeve now costs TEST and HOLD.
- **Gen308, Bitfinex margin positions (long/short ratio, 7-day changes) as ridge features:** v8.4 -> 2.690, bf2.3 -> 2.439. **Both fail.**
- **Gen310, two-day smoothed ridge positions:** v8.4 -> 2.686 (HOLD 2.21), bf2.3 -> 2.425. **Both fail**: the ridge signal lives one day; smoothing loses more than the turnover it saves.
- **Gen311, index ridge ML sleeve on US100 / US500 / US30 CFDs (index momentum / reversal / vol / IBS / RSI2 + VIX and equity VRP, vol-scaled target):** sleeve 0.09 / -0.15 / 0.57, corr with the index sleeve 0.44; bf2.3 -> 2.133. **Fails**: the ridge recipe does not transfer to US indices (as Gen138 on futures).
- **Gen312, BTC/ETH kimchi sleeve (Gen102 P2 rule) on the new books:** sleeve 0.15 / 0.86 / 1.48; v8.4 -> 2.599 (HOLD 2.443 up, TEST 3.725 down), bf2.3 -> 2.416 (HOLD 2.37 up, TEST down). **Both fail**; the BTC/ETH kimchi information is already in the ridge.
- **Gen313, leave-one-sleeve-out (17 trials):** no removal passes; every sleeve of v8.4 and bf2.3 still adds to at least one period (closest: bf2.3 without the ridge 2.530 but HOLD 2.086; v8.4 without C* 2.661). The books stay as they are.
- **Gen314, deleveraging bounce on altcoins (Gen89 rule, size 0.1 per coin):** sleeve -0.12 / 1.12 / 0.74 on perps (v8.4 -> 2.662), -0.43 / 1.13 / 0.69 on altcoin CFDs (bf2.3 -> 2.467 with TEST and HOLD up). **Both fail** (negative DEV 2021-12..2022).
- **Gen315, premium carry on the 60-coin universe with inverse-vol legs, replacing the 20-coin carry:** sleeve **0.83 / 1.05 / 2.72** (old 0.66 / 0.82 / 1.08); v8.4 -> **2.849 [1.208, 3.838, 2.855]**: HOLD +0.43 but TEST -0.06. **Fails the strict rule** (as Gen80 breadth, but with a far smaller TEST loss); watchlist, strongest near-miss so far.

## Gen316 / Gen317 (2026-10-21): wide premium carry with inverse-vol legs as an ADDED sleeve - ADOPTED (v8.5, bf2.4)
- **Gen316 (flagged: registered after seeing Gen315), v8.4 + 60-coin invvol premium carry as a ninth sleeve (both carry sleeves kept):** sleeve 0.83 / 1.05 / 2.72, corr C* -0.10; **v8.4 2.750 -> 2.983 [1.205, 3.915, 3.089]: passes. Adopted: v8.5.**
  - Checks (descriptive): without the top 2025-26 coin (SNX) 3.014; **2x costs 2.923 [1.17, 3.856, 3.02] (TEST below 3.896)**, 3x costs 2.863; the sleeve's 2025-26 P&L is spread over many coins (top 5 = 0.43 of 0.93) and comes from price (0.74) more than funding (0.19).
  - Caveats: result-driven follow-up of a near-miss; 2022 falls 1.32 -> 1.21; the TEST gain is cost-sensitive; the 40 extra coins must be tradable on Bybit (HyroTrader).
- **Gen317, the same construction in the CFD book (35 BrightFunded crypto CFDs with a measured spread <= 50 bp, half spread + 1.2 bp, no swap):** sleeve 1.09 / 1.13 / 2.05; **bf2.3 2.506 -> 2.787 [0.543, 4.043, 2.758]: every period up, passes. Adopted: bf2.4.** An out-of-book replication of Gen316 on other instruments and costs.
  - Checks: without the top coin (SNX) 2.776; 2x costs 2.692 [0.48, 3.943, 2.649]; 3x costs 2.597; only coins <= 25 bp (25 coins) 2.701.
- Paper versions (**both self-tests PASSED**): `v85` (config/paper_v85.json, scale 0.904; reproduces 2.983 / 1.205 / 3.915 / 3.089) and `bf24` (config/paper_bf24.json, scale 0.910; capped 2.781 / 0.543 / 4.029 / 2.758). Both read the extra coins live (extra_pack, as the v6b / bfb shadow runs did).
- **References from here: v8.5 2.983 / 1.205 / 3.915 / 3.089; bf2.4 2.787 / 0.543 / 4.043 / 2.758** (v7lab / bf2lab defaults).
- Lesson: breadth carry failed for a year as a REPLACEMENT with equal weights (TEST loss); as an ADDITION with inverse-vol legs it diversifies the 20-coin carry instead of replacing it.
- **Gen318, prop risk settings re-chosen for the new books (nested: choose on 2022-24, judge on 2025-26; Gen236 method):**
  - **v8.5 on HyroTrader 2-Step $200k: 2.0 challenge / 2.0 funded (was 2.0 / 1.5). 2025-26 mean net $173k -> $202k, p10 $110k -> $112k, P(profit) 1.00. Adopted.**
  - bf2.4 on BrightFunded Classic $200k: chosen 2.5 / 2.0 gives $186k vs $167k but p10 $87k < $108k. **Not adopted**; stays 2.0 / 1.5.
- **Gen319, 60-coin inverse-vol cross-sectional factors as added sleeves in v8.5:** A 28-day momentum 0.60 / 0.10 / 0.63, v8.5 -> 2.926 (TEST 3.70); B 7-day reversal -0.43 / -1.01 / -0.94, 2.632. **Both fail**: only the carry factor survives the wide construction.
- **Gen320, bf2.4's 11-coin CFD premium carry with inverse-vol legs:** sleeve 0.07 / 1.30 / 0.69 (equal legs 0.26 / 1.29 / 0.61); bf2.4 2.787 -> **2.789 [0.500, 4.046, 2.790]: passes the strict rule at noise level** (+0.002). Research reference **bf2.5**; NOT built into the paper version (bf24 stays, as with v8.1: too small to justify a change).
- Survivorship note on Gen316/317: the 40 extra coins are Binance perps listed when Gen80 downloaded them (2026-10), so coins delisted before then are missing. For a long-short carry sleeve the bias direction is unclear (delisted coins would have been both shorted high-premium names and losing longs); treat the wide-carry gain as optimistic until the paper run confirms it.
- **Gen318-320** see above. **Gen321** (survivorship check of the wide carry on a point-in-time universe incl. delisted perps) is registered and its script is ready (code check reproduces Gen316 exactly); it waits for `get_binance_pit.bat`. If it fails, v8.5 / v8.6 fall back to v8.4 + tranching.

## Gen322 (2026-10-21): tranched carry rebalancing - ADOPTED (v8.6, bf2.6)
- Every premium-carry sleeve rebalanced in 7 staggered weekly tranches (offsets 0..6, averaged) instead of on one arbitrary weekday; signal, universe, weights and costs unchanged (removes rebalance timing luck).
- **v8.5 2.983 -> 3.110 [1.542, 3.968, 3.111]: every period up. Adopted: v8.6.**
- **bf2.4 2.787 -> 2.829 [0.430, 4.067, 2.925]: TEST and HOLD up (2022 lower). Adopted: bf2.6** (bf2.5 = Gen320's research-only note).
- Paper versions (**both self-tests PASSED**) `v86` (scale 0.902; reproduces 3.110 / 1.542 / 3.968 / 3.111) and `bf26` (scale 0.908; capped 2.822 / 0.430 / 4.052 / 2.925). Harness defaults v8.6 / bf2.6.
- **References from here: v8.6 3.110 / 1.542 / 3.968 / 3.111; bf2.6 2.829 / 0.430 / 4.067 / 2.925.**

## Gen323 (2026-10-21): execution and firm-rule study of v8.6 (descriptive; `research/FIRM_RULES_EXECUTION.md`)
- Netting all sleeves into one position per coin (cascade and Weiss kept as their own orders): **3.158** [1.58, 4.02, 3.16] vs 3.110 sleeve by sleeve; but **62 orders a day, median $366**.
- No-trade band $1,000: 3.140, **22 orders a day** (median $1,800); band $2,500: 3.194, 12 a day.
- **HyroTrader funded cap of 2x initial balance on open notional: at risk 2.0 the book exceeds it in 29% of hours.** Funded setting changed to **risk 1.5 + cap 1.9x + band $1,000: 3.138 [1.71, 4.00, 3.06], 19.5 orders a day, never above 2x.** Gen318's funded 2.0 is withdrawn (it did not know the cap).
- 3% per-position loss cap: 3 coin-days above $6,000 in 4.7 years at risk 2.0 (BTC / ETH). 40% best-day rule (evaluation): 101 of 182 walks need a median 5 extra days. **HyroTrader daily drawdown 4% instead of 5% would cut the 2025-26 two-year mean from $235k to $193k** (to confirm with support).
- BrightFunded: the funded 5-minute news rule hits the R1 index entry on FOMC days (14:00 ET); place it at 14:06 ET on those days.
- **Gen324 (descriptive), bf2.6 under BrightFunded's "max(balance, equity) at rollover" daily rule (MT5 accounting):** more daily stops (89 vs 67) but no extra breaches and no Sharpe loss; realising floating losers nightly would cost $193k (rejected). Hourly-gap breaches of the 5% limit at risk 2.0: bf2.6 2025-10-10, v8.6 2023-03-22 / 2024-03-05; none at risk 1.5. **HyroTrader allows your own Bybit API bot (official FAQ): v8.6 runs in full.**

## Gen325 (2026-10-21): how much to believe, and both accounts together (descriptive; `results/gen325.json`)
- **Deflated Sharpe** (Bailey & Lopez de Prado), 1,734 days, skew +1.2, kurtosis 12-15. Expected best-of-N luck SR0: N = 50 -> 1.04, 300 -> 1.33, 1,559 (all trials in this project) -> 1.55 (annual).
  - v8.6 3.11 -> **planning Sharpe 1.78** (N = 300; 1.56 at N = 1,559); bf2.6 2.82 -> **1.49** (1.27). DSR > 0.998 for both: the edge is very likely real, its size is very likely smaller than the backtest.
- **The two books are nearly the same bet: daily correlation 0.81.** Two accounts double the money, not the safety.
- **Both accounts together, 2 years (2025-26 sample, risk 2.0 / 1.5, fees and failed attempts included):**
  | returns used | HyroTrader mean (p10) | BrightFunded mean (p10) | both: mean / p10 / per month | P(net loss) |
  |---|---|---|---|---|
  | backtest | $186k ($114k) | $174k ($111k) | $360k / $232k / $15.0k | 0.0% |
  | **planning (deflated, N = 300)** | **$91k ($21k)** | **$79k ($19k)** | **$170k / $59k / $7.1k** | **1.0%** |
  | half the backtest Sharpe | $78k ($14k) | $73k ($17k) | $151k / $44k / $6.3k | 2.4% |
- **Research rules from 2026-10-21 (paper trading v86 / bf26 running):** a change is adopted only with EVERY period not lower and the 2022-26 Sharpe +0.05 or more; adopted changes are collected as candidates (v8.7 / bf2.7) and go live only after the paper review. Check (descriptive): making the BrightFunded book different from v8.6 lowers the two-account Sharpe (bf2.6 as is 3.13 combined; indices + Coinbase premium only 2.76): diversification needs an uncorrelated book with a Sharpe of about 1.7+. **Gen326** (carry on a point-in-time top-100 / top-150 universe) registered before the data.

## Gen277 / Gen277b / Gen309 / Gen309b (2026-10-22): Bithumb and Deribit options data (user download)
- **Gen277 (as registered, vs v8.1): Upbit + Bithumb two-venue Korean premium replacing the alt-kimchi sleeve: 2.554 -> 2.586 [1.046, 3.719, 2.385]: passes.**
- **Gen277b (vs the current books, stricter bar: every period up and +0.05):** v8.6 3.110 -> 3.130 [1.567, 3.974, 3.137]: every period up but only +0.02: **not adopted** (noted as a consistent small gain); bf2.6 -> 2.824 (2022 lower): fails.
- **Gen309 (as registered, vs v8.4 / bf2.3): options skew, put/call ratio, taker call flow in the ridge:** ridge sleeve 0.22 / 2.06 / 1.73 (TEST and HOLD up, 2021-22 down); v8.4 -> 2.672 (2022 1.09), bf2.3 -> 2.461. **Both fail.**
- **Gen309b (vs v8.6 / bf2.6):** v8.6 -> 3.056 [1.32, 3.90, 3.18]; bf2.6 -> 2.786. **Both fail** (2022 and TEST lower; the options information mostly duplicates the VRP feature).
- Nothing adopted; the books stay v8.6 / bf2.6. The paper traders are unchanged.

## Gen327 (2026-10-23): Bybit reality check of v8.6 (descriptive; user download `get_bybit_check.bat`)
- **All 60 coins trade as USDT perpetuals on Bybit** (min order $5; max leverage 25-150x). Median spread 2.3 bp (max 11 bp, ENJ).
- On the Gen323 net-position model: baseline 3.158 -> **Bybit funding 3.104** -> **+ Bybit costs (5.5 bp taker + half spread) 3.038** -> **+ $1,000 band 3.027 [1.51, 3.89, 2.99]**, 22 orders a day.
- Protocol decision: the fallback (v8.4 + tranching, without the wide carry) is 2.786 even before any Bybit penalty, so **v8.6 stays** for HyroTrader.
- **Thin order books:** 42 of 60 coins show less than $500 at the best bid / ask (top level only). Stress, descriptive: +10 bp impact per side on those coins 2.896; +25 bp 2.699. **Execution requirement: rebalance the daily / carry sleeves with passive limit (maker) orders spread over the first hours of the day** (carry is weekly and tranched, so a few hours of delay costs little); market orders only for the trend / Weiss / stop exits.
- Planning numbers for HyroTrader are now based on about 3.0 (backtest) instead of 3.11.
- **Audit 2026-10-23** (`research/AUDIT_2026-10-23.md`): truncation test of v86 / bf26 at two cut dates (30k-45k hours) shows no look-ahead (max diff 0); beta 0.08-0.10; positive every year; 2022 Binance-pack data gaps (cost the backtest +1.05%, not an inflation); main risks: universe chosen with today's knowledge (Gen321 pending) and the reused holdout (deflated Sharpe); bf26 index-feed reconcile issue pending the user's files.

## Gen328 (2026-10-23): robustness round for live use (risk rules; `results/gen328.json`)
- **Sleeve decay:** no sleeve triggers the warning (12-month Sharpe < 0 and below its own 10th percentile). Weakest over the last 12 months: C* 0.36 / 0.38 (26th / 25th percentile of its history; last 6 months 1.65) and alt kimchi 0.44 / 0.29. Strongest: wide carry 3.04 (v8.6), ridge 1.81, cascade 1.79. The warning rule is now part of `config/paper_monitor.json`.
- **Per-coin caps (v8.6 net positions):** the largest single-coin position is 17% of equity at the median (p99 53%, max 96%). Caps of 40 / 30 / 25 / 20% leave the worst day (-11.4%) and the max drawdown (-18%) unchanged: crash days hit all coins at once. **Not adopted** (rule: worst day and drawdown must improve). Note for HyroTrader's 3%-per-trade rule: a 25% cap cuts the worst single-coin day from -5.8% to -4.6% at -0.025 Sharpe; a 20% cap to -3.7% (optional for the bot).
- **Crash stress (risk 2.0, daily sums without the daily stop):** worst days v8.6 -11.6% (Luna 2022-05) and -10.8% (FTX 2022-11); bf2.6 -11.2% (FTX). The 2.5% daily stop catches these days in the hour they cross it (2 / 1 days in 4.7 years jumped past 5% within one hour, Gen324). The 3AC / Celsius crash (BTC -29%) was +17% for v8.6. 2025-10-10: v8.6 +0.4%, bf2.6 -4.3%.
- **Emergency brakes:** B1 (half risk for 2 days after a stop day) and B2 (half risk after a 3-sd BTC day) are **not adopted**: neither improves both the worst day and the max drawdown (B2 raises the Sharpe slightly, 3.16 / 2.88, but leaves the worst day). **The 2.5% daily stop, checked every minute by the bot, stays the only emergency brake.**

## Gen329 (2026-10-23): v8.6 at other crypto prop firms (descriptive; `results/gen329.json`, `scripts/gen329_firms.py`)
Same book everywhere (no strategy parameter re-fitted per firm); per firm the challenge / funded risk is chosen on 2022-24 (highest net with P(profit) >= 0.9) and judged on 2025-26; 2-year bootstrap, $200k accounts.

| Firm (rules) | Risk chosen | Net 2 y @ Sharpe 3.03 (p10, P profit) | Net 2 y @ Sharpe 1.78 (p10, P profit) |
|---|---|---|---|
| HyroTrader 2-Step (5% daily, 10% static) | 2.5/2.0 (planning 2.0/1.5) | $222k ($107k, 0.99) | $90k ($25k, 0.97) |
| **Crypto Fund Trader 2-Phase** (5% daily, 10% static, 8% / 4% targets) | 2.0/2.0 | **$225k ($125k, 1.00)** | **$112k ($24k, 0.97)** |
| Propr 2-Step (5% daily, **8% trailing**) | 1.5/1.0 (planning 1.0/1.0) | $111k ($51k, 0.96) | $56k ($15k, 0.98) |
| MyFundedPerps Signature (**3% daily**, 6% static) | 1.5/1.5 | $133k ($41k, 0.99) | $54k ($2k, 0.92) |

- Verdict: CFT 2-Phase is the best alternative to HyroTrader (equal or better); Propr loses half (trailing 8% forces risk 1.0 and 143 days to funded); MyFundedPerps' 3% daily limit makes the bad tail thin (p10 $2k). Breakout (bots banned) and SizeProp (frontend-only automation) excluded.
- ASSUMED: CFT $200k fee $1,100, Propr / MFP fees and targets; platform costs equal to Bybit at every firm (CFT MT5 / Match-Trader swaps and commissions, Propr Hyperliquid fees and coin list unknown). NL access at CFT / MFP not confirmed.
- Per-firm paper accounts: `scripts/paper_firms.py` replays the v86 paper ledger through each firm's rules (HyroTrader 2.0, CFT 2.0, Propr 1.0 as a watch). No separate paper process: the signals are identical.

## Gen330 (2026-10-23): v8.6 per firm with each firm's PLATFORM and published RULES (`results/gen330.json`, `scripts/gen330_firm_platforms.py`)
**Platform Sharpe (2022-26 / 2022 / 2023-24 / 2025-26):**
- Bybit (HyroTrader; CFT Bybit route): 3.027 / 1.51 / 3.89 / 2.99
- Hyperliquid (Propr; 4.5 bp taker; leverage cap 5x BTC/ETH, 2x others): 3.113 / 1.57 / 3.99 / 3.10. The cap binds in 9% of hours at risk 1.5 and in 29% at risk 2.0.
- CFT MT5 CFDs (0.0325% per side, no funding; swap per year on |notional|):

  | Swap | All 60 coins | 35-coin CFD list |
  |---|---|---|
  | 0% | 2.98 | 2.96 |
  | 10% | 2.42 | 2.56 |
  | 20% | 1.86 | 2.15 |

  The CFD swap rate decides this route.

**Per-firm risk tools (challenge risk, funded risk, daily-stop fraction) chosen on 2022-24 and judged on 2025-26.** Net over 2 years at the platform Sharpe and at the planning level (minus 1.25):

| Firm | Default 2.0 / 1.5 / 0.5 | Chosen setting | Chosen result | Verdict |
|---|---|---|---|---|
| HyroTrader $200k | $172k (p10 $102k) / planning $86k | 2.5 / 2.0 / 0.4 | $188k (p10 $78k) / planning $69k | **keep default** |
| CFT $200k, Bybit route | $168k (p10 $98k) / planning $84k | 2.5 / 2.0 / 0.4 | $190k / planning $74k | **keep default** |
| CFT $200k, MT5 CFDs, swap 10% | $113k / planning $38k (P profit 0.78) | — | — | weak |
| Propr 2 × $100k | $96k (P profit 0.84) / planning $25k (0.55) | 1.0–1.5 / 1.5 / 0.4–0.6 | $131k / planning $53k (0.92) | **lower risk needed** |
| MyFundedPerps 2 × $100k | $148k / planning $55k (0.87) | 1.0–1.5 / 2.0 / 0.4 | $152k / planning $69k (0.95) | **lower challenge risk** |

- **Conclusion: no strategy re-fit per firm.** At the static 10% firms, the risk "optimised" on 2022-24 did worse out of sample (planning level: −$17k mean, p10 below zero), so the default stays. Only at firms with tighter rules does the firm-specific setting add money, and there it means lower challenge risk (1.0–1.5).
- `scripts/paper_firms.py` now uses these settings: HyroTrader and CFT 2.0 / 2.5% stop; Propr $100k 1.0 / 3% stop with a trailing loss that locks at the starting balance; MFP $100k 1.0 / 1.2% stop.

## Gen331-334 (2026-10-23): validation round, Hyperliquid, all firms together, three new sleeves

**Gen331, venue and timing (`results/gen331.json`):**
- **OKX prices PASS.**
  - Setup: the same v8.6 net positions on OKX hourly closes (57 coins, 94% of position-hours), event sleeves left out of both runs.
  - Sharpe 2.597 vs 2.598 on Binance, every period within 0.03; hourly P&L correlation 0.997; annual return 35.3% vs 35.3%.
  - So the profit does not come from Binance's prices.
- **OKX funding (2026-07-20..09-30):** the book earns 2.1% a year on OKX vs 3.2% on Binance (15%-vol units). Small.
- **Execution 1 hour late:** 3.158 -> 2.977 (-0.18). The bot must trade on time; late hours cost real Sharpe.
- **Measured MT5 swaps (BrightFunded's normal schedule, 42 coins): median -13.4 bp a day on both long and short (-49% a year).**
  - BTC -5.7% a year; ETH -104% a year.
  - CFD route: swap-free 2.61 -> with swaps **-1.80**. The swap cost (0.69 a year) exceeds the whole book return (about 0.45).
  - **A CFD route works ONLY swap-free** (BrightFunded has that add-on; CFT MT5 does not as far as published -> CFT only via its Bybit route).

**Gen333, Hyperliquid for Propr (`results/gen333.json`; coin list not readable from the cloud -> `get_hyperliquid_check.bat`):**

| Scenario | Sharpe | Propr 2 x $100k, 2025-26 (realistic / planning) |
|---|---|---|
| All 60 coins | 3.11 | $137k / $53k |
| 51 coins (the 9 unconfirmed coins removed) | 2.87 | $97k / $33k (P profit 0.80) |
| Core 20 coins | 2.59 | $69k / $18k |

- Altcoin leverage cap 2x vs 3x hardly matters (0.02).
- **The Hyperliquid coin list decides Propr.**

**Gen332, all accounts together (`results/gen332.json`; one joint bootstrap 2025-26):**
- Accounts: HyroTrader $200k + CFT $200k (Bybit) + BrightFunded $200k (bf2.6) + Propr 3 x $100k (51 coins) + MyFundedPerps $100k.

| Account | 2-year net, realistic | 2-year net, planning (p10) |
|---|---|---|
| HyroTrader | $173k | $87k ($19k) |
| CFT | $169k | $86k ($23k) |
| BrightFunded | $171k | $69k ($17k) |
| Propr | $145k | $49k (-$9k) |
| MyFundedPerps | $77k | $35k ($4k) |
| **Total** | **$735k (p10 $440k)** | **$326k (p10 $89k)** |

- Planning level: P(total < 0) 1.5%; P(every account loses) 0.3% (then about -$29.5k = the fees); fees mean $25k, max $30k.
- Account outcomes are correlated 0.72-0.78.
- Stack order by planning p10 added: HyroTrader $19k -> + CFT $46k -> + BrightFunded $77k -> + Propr $78k -> + MFP $89k.
- **Propr (on 51 coins) adds mean but no safety.**

**Gen334, three new sleeves for v8.6 (strict rule; 3 trials):**
- **A, funding-change XS:** sleeve 0.15 / -0.84 / 1.70; v8.6 -> 2.788. Fails.
- **B, low-beta XS (betting against beta, 60 coins):** sleeve 0.32 / -0.65 / 0.86, corr C* -0.19; **v8.6 -> 3.228 [1.749, 3.898, 3.318]**.
  - 2022 and HOLD up, +0.12, but TEST lower (3.968 -> 3.898) and the sleeve's TEST is negative.
  - **Fails the strict rule.** Watchlist (second near-miss after Gen315). No variants will be tried: that would be fitting.
- **C, late-UTC BTC/ETH seasonality (literature):** -1.83 / -1.62 / -2.88. Fails badly (the effect is gone after costs).
- **No change to v8.6 / bf2.6.**

## Gen335-338 (2026-10-23): robustness round - luck audit, parameter ensembles, limit-order execution, portfolio construction

**Gen335, parameter luck audit (each sleeve varied inside v8.6; `results/gen335.json`):**

| Sleeve | Grid | Chosen setting's percentile | Grid median minus chosen | Worst grid point | Verdict |
|---|---|---|---|---|---|
| premium carry 20 | 25 points | 64th | -0.02 | 3.00 | not lucky |
| premium carry 60 | 25 points | 12th | +0.045 | 3.09 | not lucky |
| trend 4h | 5 points | 40th | 0.00 | 2.95 | not lucky |
| alt kimchi | 3 points | 33rd | 0.00 | 3.08 | not lucky |
| cascade | 9 points | **89th** | **-0.10** | 2.86 | **lucky choice** |
| delev bounce | 9 points | **89th** | **-0.15** | 2.74 | **lucky choice** |

- Every carry grid point keeps v8.6 >= 3.0.
- The cascade and deleveraging-bounce settings are lucky. They were fixed in early generations; expect about 0.1-0.15 less from them live. (The planning Sharpe already deflates far more than this.)

**Gen336, neighbourhood ensembles (strict rule, 7 trials; `results/gen336.json`):**
- premium carry 20: 3.096
- premium carry 60: **3.154 [1.661, 3.991, 3.123]** (every period up, +0.044)
- trend 4h: **3.151 [1.633, 3.977, 3.156]** (every period up, +0.041)
- cascade: 2.979
- delev bounce: 2.990 (2022 0.91)
- alt kimchi: 3.116
- all six together: 2.921
- **None passes** (the two best miss the +0.05 by a hair). The cascade and delev ensembles fall because of the lucky originals.
- **Gen336b (FLAGGED post hoc):** carry 60 + trend 4h + alt kimchi ensembles together: **3.200 [1.763, 4.005, 3.167]**, passes the strict rule, but it was registered after seeing Gen336.
- **Gen336c (registered before running): the same idea in bf2.6** (carry BF + alt kimchi ensembles): 2.840 [0.424, 4.115, 2.900]. Neutral, so the replication does not hold (2022 and HOLD slightly lower).
- -> **v8.7 candidate (low confidence): the Gen336b ensembles.** Their value is less dependence on one parameter choice, not +0.09 of real alpha; decided at the paper review.

**Gen337, limit-order (maker) execution on Bybit (cost, not alpha; `results/gen337.json`):**
- Taker baseline: 3.027 [1.514, 3.891, 2.988].
- Limit at the previous close for the whole hour:
  - fill on a touch: 3.224 (unrealistic, 99% fills);
  - fill only on a 2 bp trade-through: **3.079 [1.613, 3.928, 3.027]** (95% filled);
  - fill only on a 5 bp trade-through: 2.954 (the missed moves cost more than the fees saved).
- **Gen337b (refinement registered after Gen337):** limit valid 15 minutes, then market (5-minute data, pack coins): **3.069 [1.588, 3.934, 3.010]**, 91% filled. Every period above taker.
- -> **Execution plan adopted: post limit orders at the previous close for 15 minutes, then go to market.** About +0.04 Sharpe, and the risk is bounded to 15 minutes of drift. Real fill rates must be measured in the first live weeks.

**Gen338, portfolio construction (strict rule, 3 trials; `results/gen338.json`):**
- EWMA vol target: 3.088 (2022 1.37). Fails.
- Blended 30/90-day vol: 3.096 (TEST lower). Fails.
- Equal risk contribution (shrunk covariance): 3.146 [1.708, 4.006, 3.039]. HOLD lower; fails. The simple inverse-vol equal risk stays.

## Gen339-340 (2026-10-23): lower costs, weekly paper report, a second edge outside crypto

**Gen339, execution cost (`results/gen339.json`):**
- Current $1,000 band to target: taker 3.027, maker 3.079.

| Variant | Taker | Maker | Note |
|---|---|---|---|
| $500 band | 3.035 | 3.092 | 30 orders a day |
| $2,000 band | 3.042 | 3.091 | HOLD lower |
| $4,000 band | 3.019 | 3.056 | |
| cost-aware band | 3.051 | 3.102 | TEST lower by 0.001-0.004 |
| to band edge $1,000 | 3.060 | 3.103 | HOLD lower |
| to band edge $2,000 | 3.030 | 3.066 | |

- **None is better in every period under both cost models, so the $1,000 band stays.** Differences are within ±0.05: the cost lever is used up once limit orders are in (total execution cost about 0.017 a year in 15%-vol units vs a 0.45 return).
- Turnover cost / price P&L by sleeve:
  - C* 7%, delev 8%, ridge 17%, alt kimchi 25%, carry 20 27%, carry 60 27%.
  - Netting saves about 8% of the summed sleeve costs.
  - The carry sleeves are the cost-heavy part; maker execution matters most there.

**Weekly paper report:** `scripts/paper_report.py` -> `research/PAPER_REPORT.md`.
- Contents: the gate numbers, every alert in `config/paper_monitor.json` (sleeve -3 sd using `results/paper_sleeve_sd.json`, drawdown, stops in 14 days, late hours, reconcile) and the per-firm accounts.
- First run: v86 reconcile OK; bf26 reconcile INVESTIGATE (the known index-feed issue, waiting for the user's files); no other alert.

**Second edge outside crypto:**
- **Existing futures book (Gen205-238, 15 sleeves): daily correlation with v8.6 0.04** (monthly 0.14).
  - 2022-26 Sharpe 1.24; out of sample 2023-26 1.22 (about 0.5 after removing ES/NQ beta).
  - On v8.6's 20 worst days it lost 0.13% on average (no protection, no harm).
- Equal-risk mixes (backtest Sharpe):
  - v8.6 + futures 3.02 (vs 3.11 alone); v8.6 + bf2.6 + futures 3.15.
  - At planning levels (v8.6 1.78, futures 0.8): 1.79.
  - Optimal weights: at most about 1.95, i.e. +0.1 to +0.15.
- **A second edge adds safety more than Sharpe, and only if its own Sharpe is at least about half of v8.6's.**
- The futures book needs a futures firm that allows overnight holding AND bots: PropShop Trader swing accounts (bots via Tickblaze per reviews, conflicting) or similar.
  - Topstep / Apex / MFFU / Tradeify / FTMO Futures / FundedNext Futures all flatten at the close.
  - Value per 50k account is only about $6.7k over 2 years (Gen237). Low priority.
- BrightFunded lists no bond CFDs, so the Treasury sleeves (BC, F3) cannot move to CFDs; the equity sleeves overlap bf2.6's index sleeve. Index-CFD book (Gen201): 0.86, corr bf2.6 0.37; adding it lowers the mix.
- **Gen340, two FX effects on unused 2013-26 Dukascopy data (pre-registered, 2 trials):**
  - **A, month-end fix rebalancing (Melvin & Prins):** net 0.07 / -1.21 / -0.08 (gross 0.31 / -1.03 / 0.19). Fails.
  - **B, local-hours depreciation (Breedon & Ranaldo):** gross 0.80 / 0.14 / 0.15 (the effect has faded since 2019); net -1.15 / -1.60 / -1.74. Fails.
- **Conclusion:** no tradable independent edge with a Sharpe near v8.6's exists in our data. The futures book is the only real one; it is small in prop dollars and needs a swing + bot futures firm.

## Gen341 (2026-10-23): crypto sleeves meant to be uncorrelated with v8.6 (3 trials; `results/gen341.json`)

| Trial | Sleeve DEV / TEST / HOLD | Corr with v8.6 | v8.6 with it |
|---|---|---|---|
| A, funding-settlement pressure (short high-funding coins in the hour before settlement) | -1.70 / -1.58 / -2.09 | 0.10 | 2.581 |
| B, 1-day residual reversal vs BTC (60 coins, 3-day tranched hold) | -1.87 / -1.45 / -0.43 | -0.01 | 2.683 |
| C, pump reversal (short after a +4 sd hour, 12 h) | -2.22 / -2.20 / -1.63 | -0.23 | 2.694 |

- **All fail clearly.** The short-horizon effects are either absent or eaten by costs; pumps keep going rather than reverting.
- With Gen334 (funding change, low beta, seasonality), Gen319 (XS momentum / reversal) and Gen261 / Gen274 (attention, trade size, OI), the crypto ideas left in our Binance data either correlate with v8.6 or lose money.
- **No orthogonal crypto sleeve found.**

## Gen342-348 (2026-10-23): search for a crypto edge UNCORRELATED with v8.6 (22 trials incl. Gen341)
Bar for every trial (pre-registered): sleeve DEV (2020-22) > 0, TEST (2023-24) >= 0.8, HOLD (2025-26) >= 0.5 and |daily corr with v8.6| <= 0.2.

**Failed rounds:**
- **Gen342, catalogue of 24 earlier crypto sleeves, selected on 2020-24 only:**
  - Selected: USDT premium, kimchi BTC/ETH, Google attention, spot dominance, R1X dip, FOMC weeks, options flow D2.
  - Orthogonal book 1.03 / 2.72 / **0.76**, corr 0.38 / 0.23. Just misses (HOLD < 0.8).
- **Gen343, macro timing:** dollar -0.13 / 0.56 / -0.02; rates 1.28 / 1.08 / -0.43; both -0.69 in HOLD; ETH/BTC trend 0.39 / -0.78 / 1.71. Fails. BTC buy-and-hold had HOLD 0.05, so directional timing has little to work with in 2025-26.
- **Gen344, factors:** size 1.69 / 0.27 / -1.57; MAX -0.91 / -0.69 / 0.11; illiquidity 1.89 / 0.40 / -1.29. The classic crypto factors have decayed.
- **Gen345, mechanical flows:** stablecoin mint shock **0.89 / 1.78 / 0.38** (corr 0.19, near-miss); leverage crowding too few events; weekend reversal -0.70 / -0.68 / -0.11; US-open seasonality -1.68 / -0.53 / -0.43.
- **Gen346, hourly flows:** Coinbase hourly premium **1.45 / 0.62 / 0.26** (corr 0.11, near-miss); Upbit volume spikes -0.82 / -0.92 / -0.75; spot taker imbalance -1.38 / -2.57 / -4.06.
- **Gen347, taker-flow reversal on independent data:** perps -2.20 / -4.57 / -5.30; spot -3.52 / -5.53 / -6.20. Both directions lose: it was trading cost (10x turnover a day), not signal.

**Gen348 A, premium-spike reversion: PASSES the bar** (60 coins; hourly perp premium z vs 720 h > 3 -> short 0.1 for 4 h, < -3 -> long 0.1 for 4 h).
- Result: **1.11 / 0.80 / 1.02, corr v8.6 0.09**; gross 1.54 / 1.61 / 1.82.
- **Robustness (Gen348b, registered before running):**
  - Bybit costs + funding: 0.91 / 0.41 / 0.61.
  - Limit orders (96% filled): 0.97 / 0.68 / 0.70.
  - OKX prices: 0.64 / 0.69 / 0.73.
  - Neighbourhood median (z 2.5-3.5 x hold 2-6 h): 1.11 / 0.66 / 0.87.
  - **Every calendar year 2020-2026 positive** (3.44, 1.27, 0.33, 0.67, 0.92, 1.13, 0.89).
  - About 3,800 entries a year, mean gross exposure 0.22.
  - **Weak spots:** costs x2 -> 0.69 / -0.01 / 0.21; execution one hour late -> 0.05 / -0.01 / 0.66. The bot must act within minutes after the hour, with limit orders.
  - Sides: the longs after negative spikes carry it (1.33 / 1.70 / 0.86); the shorts lose (-0.79 / -0.66 / 0.66).
- **Long-only version (Gen348e, FLAGGED post hoc):** Bybit costs 1.21 / 1.39 / 0.46, corr v8.6 0.18 (with delev bounce 0.36). Positive every year, but more correlated: kept as information only.
- **Inside v8.6 (Gen348c / d):**
  - Equal risk: 3.055 [1.325, 3.921, 3.294]. Fails (2022 / TEST lower).
  - Weight chosen on 2022-24 (x0.25): 3.115 [1.494, 3.988, 3.173]. Fails (+0.005, 2022 lower).
  - The backtest Sharpe of v8.6 (3.1) is so high that a 1.0 sleeve barely adds. At planning levels (v8.6 1.78), an uncorrelated 0.7-0.9 sleeve would add about +0.1-0.2.
- **Status: orthogonal candidate (not adopted).** Next step: paper-trade it as its own small book next to v86.
- Planning Sharpe after costs about 0.6-0.8 (backtest 0.9-1.0 minus the 22-trial search).

## Gen349-358 (2026-10-23): orthogonal search continued (about 30 more trials; total in the search about 52)
Bar for every trial (pre-registered): DEV > 0, TEST >= 0.8, HOLD >= 0.5, |corr v8.6| <= 0.2, and from Gen349 also |corr premium-spike sleeve| <= 0.5.

**Failed:**
- **Gen349, dislocations:** Binance-OKX gap 0.93 / 0.22 / -1.03; Upbit hourly kimchi 1.14 / 0.76 / -0.44 (both decayed by 2025-26); ETH/BTC hourly spikes -0.96 / -2.09 / -2.44; DVOL spike 0.04 / 0.18 / -0.25.
- **Gen350, positioning spikes:** OI-spike fade, top-trader crowding, taker ratio spikes. All fail.
- **Gen351, relative value:** distance pairs -0.64 / 0.46 / -0.64; weekday seasonality; long-term reversal -0.30 / 1.02 / -0.67. All fail.
- **Gen353:** spot-volume surge, BTC-shock laggards, hourly premium rank. The last has gross 3.91 / 2.63 / 1.04, corr 0.06, but turnover kills it.
- **Gen354 (FLAGGED follow-up):** the same premium rank at daily, 3-tranche or banded turnover is negative in HOLD. Fails.
- **Gen355 A / B:** cross-venue funding spread -0.42 / 0.17 / -2.48; retail long/short contrarian 1.42 / 0.91 / 0.12. Fail.
- **Gen356:** OKX volume share, Coinbase volume share, euro premium spikes. All fail.
- **Gen357 A / B:** intraday momentum fails (cost); volume-shock momentum 0.10 / 0.75 / 0.86 is a near-miss.

**Gen352, crash limit buys (resting limit 3 sd below the last close):**
- Raw result 4.38 / 4.48 / 2.80, corr 0.23.
- Verification (Gen352b-g):
  - OKX-only replication 4.40 / 4.60 / 2.27; volume caps barely bind.
  - **The profit is the rebound inside the fill hour (+78 bp per fill), i.e. buying wicks.**
  - As a market order on the first 5-minute close below the level (realistic): 1.82 / 1.10 / -0.68.
  - Strictest resting-limit version (20 bp through on both Binance and OKX, volume cap, Bybit exit): 2.47 / 2.16 / -0.13.
- **Not adopted:** it depends on wick fills a backtest cannot verify, and it fades in 2025-26.

**Gen355 C, extreme negative funding (< -0.10% per 8 h -> long 24 h): passes** 1.54 / 0.97 / 0.73, corr 0.17.
- Checks: Bybit costs 1.52 / 0.91 / 0.71; Bybit signal 0.64 / 1.23 / 0.96; OKX 0.85 / 1.02 / 1.00; neighbourhood median 1.53 / 0.93 / 0.98; one hour later 1.62 / 0.96 / 1.01; every year positive.
- **But the price part alone is -0.38 in HOLD: the profit there is the funding received.** Fails its own pre-registered candidate rule. Near-candidate ("event carry").

**Gen357 C, daily crash reversal (daily return < -3 sd -> long 3 days, 60 coins): passes and is a CANDIDATE** 0.14 / 1.00 / 1.17, corr v8.6 0.14.
- Checks: Bybit costs 0.14 / 0.98 / 1.14; OKX 0.11 / 0.94 / 1.05; neighbourhood median 0.14 / 0.83 / 1.06; one hour later 0.24 / 0.84 / 0.98; 6 of 7 years positive (2022 -0.78).
- Correlations: delev bounce 0.50, negative funding 0.38, premium spike 0.19.

**Gen358, stress-reversion book:**
- Book A (premium spike + crash reversal): 0.78 / 1.22 / 1.45, corr 0.15.
- Book B (+ negative funding): **1.29 / 1.42 / 1.46**, every year 2020-26 >= 0 except 2022 (-0.02), max DD -16% at 15% vol, corr 0.18.
- Inside v8.6 (weight chosen on 2022-24 = 0.25): 3.095. Fails the strict rule.
- As a separate account: book B's 2022-26 Sharpe is 0.84 with corr 0.18, so at planning levels the best mix lifts v8.6 only from 1.78 to 1.79.
- **The stress family is real and independent of v8.6, but too small to move the combined Sharpe much.** Its value is a second, different edge if v8.6's carry decays.

## Gen359 (2026-10-23): stress book, final rules -> EXPECTED LIVE Sharpe 1.04 (program `config/gen359_program.json`)
Fixed definition (registered before any number): **expected live = 0.6 x the book's 2020-26 Sharpe with per-coin Bybit costs and funding.** Target >= 1.0 with corr v8.6 <= 0.25. Every choice is made on 2020-24 only.

**Decisions on 2020-24 (Gen359):**
- **D1, premium spike:** long side only, with limit orders (2020-24 1.31; both sides with market orders 0.73). Periods 1.28 / 1.61 / 0.53.
- **D2, crash reversal:** only when BTC is above its 200-day mean, with limit orders (2020-24 0.79 vs 0.39 unfiltered). Periods 0.74 / 0.86 / 1.70.
- **D3, negative funding:** in, with limit orders (book 2020-24 1.47 -> 1.82).
- **D4, vol targeting:** none (1.82 vs 1.30).

**Final book:**
- **1.95 / 1.60 / 1.49** (2025-26 unused for every decision); 2020-26 1.736 -> **EXPECTED LIVE 1.04**.
- **Corr v8.6 0.22.** Every year positive (2020 2.15, 2021 3.27, 2022 0.52, 2023 2.39, 2024 1.10, 2025 1.30, 2026 1.86).

**Checks (Gen359b, registered before running):**
- **Neighbourhood** (premium threshold 2.5-3.5 x crash threshold 2.5-3.5): expected live 0.87-1.21, **median 1.04**.
- **Costs x2:** 1.03 (the book trades with limit orders).
- **OKX:** 0.90 over all cells; but **on the same coins and hours Binance 0.88 vs OKX 0.87**. The venue replicates; the gap comes from cells without OKX data (EGLD, HBAR, RUNE and early listing periods). Realistic range about 0.9-1.05.
- **Risk at 15% vol:** max drawdown -10.9%, worst month -3.7%, **worst day -9.4%** (a tail day: the bot's daily stop must cap it).
- **With v8.6 at planning levels** (v8.6 1.78, book 1.04, corr 0.22): equal risk 1.81; **best weight 0.4 x the book's risk -> 1.90**.
- **Inside v8.6 as a 10th sleeve:** weight chosen on 2022-24 = 0.25 -> 3.106 [1.46, 4.00, 3.17]. Fails the strict rule (the backtest v8.6 is too strong for a 1.7 sleeve to lift on paper).
- **Use:** as its own book / account at about 0.4 x v8.6's risk, not merged.
- **Next:** paper trading. Trials in the whole orthogonal search: about 56.

## Gen360-369 (2026-10-24): stress book to expected live 1.32 - and what that means in prop accounts
**Search / refinement (all choices on 2020-24):**
- Gen360 (4 trials): residual crash reversal (-0.03 / 0.84 / 0.78), equity-stress buy, VIX-spike buy, market-wide capitulation. All fail.
- **Gen361:** premium spike sized by |z| (2020-24 1.815 -> 1.875). Caps and holds unchanged. Expected live 1.085.
- **Gen362:** BTC-trend filter on the premium spike (1.875 -> 2.084); not on negative funding. Weekly crash reversal and residual + filter fail (one day later). Expected live 1.13, corr 0.15.
- **Gen363:** negative funding from either venue (Binance OR Bybit): 2.084 -> 2.157. Expected live 1.18.
- **Gen364 B, daily premium discount + BTC filter:** 1.05 / 0.88 / 1.26, robust (the alt delev bounce fails).
- **Gen365, 8-hour crash reversal + BTC filter:** 0.67 / 1.38 / 2.94, corr v8.6 0.07, robust.
- Neither of the two raised the equal-risk book on its own.
- **Gen366, construction chosen on 2020-24 among {3 equal, 5 equal, 5 Sharpe-weighted, 5 minimum-variance}:** 5 Sharpe-weighted. **2.35 / 2.33 / 1.79, expected live 1.32, corr v8.6 0.17**, every year >= 1.04.
  - Continuous mix with v8.6 at planning levels: **1.78 -> 2.06** (book at 0.65 x v8.6 risk).
- Gen367: 4-hour and 3-day crash reversal fail.
- **Gen368 checks:** costs x2 -> 1.31; worst day -7.0%, **worst hour -8.1%** (2025-10-10, premium spike buying a market-wide crash), max DD -8.6% (15% vol).

**Prop reality (Gen368 / 369 / 369b, HyroTrader / CFT $200k, 2.0 / 1.5, 2.5% stop, 2025-26 bootstrap, planning level):**

| Setup | Profit over 2 years | Bad case (p10) | P(profit) |
|---|---|---|---|
| v8.6 alone | $90k | $25k | 0.97 |
| **v8.6 + 0.65 x book in the SAME account** | **$49k** | **-$5k** | **0.82** |

- The book's crash-hour jumps break the 5% daily limit before an hourly stop can act.
- Tail controls (Gen369, chosen on 2022-24 by prop net): none / systemic-crash filter / exposure cap / 4% position stop / filter + cap.
  - 2022-24 picks "none". **The exposure cap cuts the worst hour to -1.9% (-3.6% scaled)** at little cost on 2022-24.
- **The book as its OWN account (cap version):** about $22-24k over 2 years, P(profit) 0.82-0.83.
- **Joint, two accounts (planning):** v8.6 @ HyroTrader + v8.6 @ CFT = **$180k (p10 $55k, P loss 2.8%)** vs v8.6 @ HyroTrader + book @ CFT = $112k (p10 $36k, P loss 1.8%).
- **Conclusion:**
  - The stress book raises the continuous Sharpe of a combined portfolio (1.78 -> 2.06), but **in prop accounts a second v8.6 account earns far more**. The book only wins a little on the chance of a total loss.
  - Use the book only where v8.6 cannot be run (capacity / one-account rules), or as insurance if v8.6's carry decays.
  - **Never in the same account as v8.6 without the exposure cap.**

## Gen370 (2026-10-24): prop-driven improvements of a v8.6 account, judged in DOLLARS (7 trials; engine options added to `qpl.lab.propfirms`, defaults off, 170 tests pass)
Chosen on a 2022-24 bootstrap (highest net with P(profit) >= 0.9 and p10 >= 90% of the baseline), judged once on 2025-26. 2-year net, $200k.

**HyroTrader 2022-24:**

| Option | Net 2 y |
|---|---|
| baseline | $184.4k (p10 $105.7k) |
| capped stress book w 0.1 / **0.2** / 0.3 | $177.9k / **$185.4k** / $182.9k |
| stop-day brake | $175.0k |
| volatility brake | $183.7k (p10 $115.8k) |
| target brake | $183.7k |
| funded cushion | $164.1k |

- Chosen: stress book w 0.2.
- **2025-26: backtest $182.9k -> $194.7k; planning $89.9k -> $94.5k (p10 $25.1k -> $23.5k).**

**CFT 2022-24:**

| Option | Net 2 y |
|---|---|
| baseline | $177.9k |
| volatility brake | $179.7k |
| stress book w 0.2 | $179.1k |
| target brake | $178.5k |
| stop-day brake | $168.1k |
| funded cushion | $161.8k |

- Chosen: volatility brake (the combination was not better).
- **2025-26: backtest $178.0k -> $172.5k; planning $90.0k -> $87.1k.** Worse.

**Conclusion:** every option moves the 2-year net by at most about ±5%, within bootstrap noise, and the 2022-24 winner does not carry over consistently (HyroTrader slightly up, CFT slightly down). The stop-day brake and the funded cushion clearly cost money (they cut risk exactly when the book recovers).
- **The current prop settings (2.0 / 1.5, 2.5% daily stop) stay.**
- The capped stress book at 20% weight is the only option positive at both levels at HyroTrader. Optional, not adopted (the gain is noise-sized and the p10 falls).

## Gen371 (2026-10-25): v8.6 without the ridge ML sleeve (`config/gen371_protocol.json`)
- Prompted by about 4% unit loss of ridge ML in the first paper days. Paper code first checked: `paper_v5.py _dump` over 2020 to Sep 2026 equals `cache_v86_final` exactly (32,856 hours, max diff 0).
- **Without ridge:** Sharpe 2022 1.69 vs 1.54, 2023-24 3.78 vs 3.97, 2022-24 3.05 vs **3.11**; holdout 2025-26 3.00 vs 3.11.
- **HyroTrader prop 2022-24:** net $166k vs **$184k**, p10 $89k vs $106k. Holdout: $167k vs $183k.
- Ridge sleeve Sharpe by year: 2022 -0.28, 2023 1.66, 2024 2.19, 2025 1.26, 2026 1.97. Corr with the rest of the book 0.29. 10% of its 4-day windows lose 3.7% unit or more, so the paper loss is ordinary.
- **Fails. Ridge ML stays.** Paper code unchanged.

## Gen321 / Gen326 / Gen372 (2026-10-25): survivorship check on the point-in-time Binance universe (705 perps, delisted included)
- **Gen321 (registered before the data):** the Gen316 wide carry on a point-in-time top-60 (444 coins ever in it): sleeve **0.76 / 0.08 / 0.23** (survivor version 0.83 / 1.05 / 2.72); v8.4 + this sleeve 2.732 < 2.750. **v8.5 WITHDRAWN** (and with it the wide-carry part of v8.6). Data checks: no missing months; exact-zero premiums also occur in the pack (10-30%, Binance's premium index is 0 inside the impact spread), not a bug.
- Decomposition (K = 60, tranched): survivor coins earn in every period (+0.22 / +0.38 / +0.38), the coins that are not in today's pack lose in every period (-0.23 / -0.18 / -0.36). The wide carry gain was survivorship.
- **Gen326:** v8.6 with point-in-time carry: K = 60 2.638, K = 100 2.736, K = 150 2.535 (v8.6 3.110). **All fail.**
- **Gen372 (registered after Gen321):** fallback F0 (v8.6 minus wide carry) 2.786 [1.46, 3.92, 2.40]; F1 (20-coin carry on a point-in-time top-20) **2.290** [0.87, 4.01, 1.40], carry sleeve -1.10 / 1.83 / -1.31; F2 (no carry sleeve) **2.486** [1.32, 3.61, 2.05]. The registered rule picks F1 (F2 is lower in 2023-24), planning Sharpe 2.29 x 1.78 / 3.11 = **1.31**.
  - Caveat, stated here and not used to change the result: the rule only asked whether dropping carry passes the strict bar, so it keeps a sleeve that is negative in two of three periods; and a top-20-by-volume universe is hype-heavy, not the same kind of coin as the 20 established pack coins. A fair answer needs the same point-in-time treatment of every sleeve (Gen373).
  - HyroTrader 2025-26 (holdout) net / p10: v8.6 $183k / $112k, F0 $139k / $69k, F2 $118k / $53k, F1 $67k / $5k.
- **Honest range for the book now: backtest 2.3-2.5 instead of 3.1; planning Sharpe about 1.3-1.4 instead of 1.78.** The other sleeves (C*, trend, Weiss, ridge on MAJ10 / BTC-ETH) also use coins chosen today: Gen373 checks them.
- Paper traders unchanged (they are a superset; every subset book can be recomputed from the frozen sleeve ledger).

## Gen374 (2026-10-25): the diversifiers on honest numbers (`config/gen374_protocol.json`, `results/gen374.json`)
- **Stress book (Gen366 rules, taker costs, Binance funding, look-ahead in the premium-spike BTC filter fixed):** today's 60 coins 2.32 / 1.95 / 1.89 (2020-24 2.17, expected live 1.26), as before. **Point-in-time top-60: 1.89 / 0.57 / -0.86** (2020-24 1.33, expected live 0.39; 2022-26 -0.17). **Dropped** (rule: >= 0.7 x and expected live >= 0.8). Negative funding (-2.03 in 2025-26) and the daily premium discount break on coins that are not in today's list; only crash 8h stays positive in every period (1.01 / 0.54 / 1.12).
- **Futures book:** 2022-26 Sharpe 1.24, daily corr 0.06 / 0.09 with F0 / F2. Equal-risk mix lowers the book (F0 2.79 -> 2.76); best in-sample weight 0.4: F0 2.99, F2 2.69 (+0.2, optimistic). Needs a futures firm with overnight holding and bots; small dollars (Gen237).
- Conclusion: no survivorship-free crypto diversifier exists yet; the futures book is the only independent edge, worth about +0.2 backtest Sharpe at a 0.4 weight in a separate account.

## Gen373 (2026-10-25): C* on a point-in-time universe and the honest live book (`config/gen373_protocol.json`, `results/gen373.json`)
- **C\*:** the own-size rebuild on fixed MAJ10 equals the v86 sleeve (daily corr 1.00; -0.83 / 2.32 / 0.56). Point-in-time top-10 by volume (members: SOL, BTC, ETH always; XRP, DOGE, BNB mostly; 1000PEPE, SUI, MATIC, LUNA, HYPE at times): **-1.91 / 2.22 / 0.64**, 2022-26 1.19 vs 1.30. Small survivorship cost, mostly 2022 (LUNA).
- **Candidates, chosen on 2022-24 HyroTrader net:**

| Book | 2022-26 [2022, 2023-24, 2025-26] | HyroTrader 2022-24 net / p10 |
|---|---|---|
| **K1 no carry, point-in-time C\*** | **2.394** [1.05, 3.55, 2.06] | **$159.6k / $87.2k** |
| K2 point-in-time 20-carry, point-in-time C\* | 2.184 [0.60, 3.93, 1.39] | $156.5k / $75.1k |
| K3 K1 without alt kimchi | 2.312 [1.35, 3.26, 1.92] | $134.0k / $57.9k |
| K4 BTC/ETH core (ridge, Weiss, bounce, cascade, trend) | 2.406 [1.80, 3.24, 1.91] | $133.0k / $65.7k |

- **Chosen: K1 = C\* (monthly top-10 by volume) + cascade + trend 4h + Weiss + delev bounce + ridge ML + alt kimchi.** Backtest 2.39, **planning Sharpe 1.37**, max DD at risk 2.0 -20%, worst day -12.9%.
  - Holdout 2025-26 (once): HyroTrader net $119.5k / p10 $53.8k / P(profit) 0.998; CFT 2-Phase 200k $116.7k / $49.3k / 0.995.
  - **Planning level (2025-26 bootstrap shifted to Sharpe 1.37): about $71k per account over 2 years, p10 about $8.5k, P(profit) 0.93-0.94** (old v8.6 plan check at 1.78: $91k / $27k / 0.97). At a weak 1.0: $49k / -$5k / 0.86.
- **Shadow on the paper ledger (46 shared hours, Oct-1 weights, C\* proxied by the paper's MAJ10 C\*):** K1 -3.0% vs v86 -3.1% at risk 2.0. The bad start is the same in both (ridge, trend, C\*).
- **The live candidate is K1 (v9.0).** The running v86 / bf26 paper traders stay unchanged; K1 is computed from the frozen sleeve ledger plus a point-in-time C\* paper sleeve to be added as a separate paper version.
- **Rerun without Binance TradFi perps (2026-10-25, `config/tradfi_perps.json`, 199 stock / ETF / commodity perps listed from 2026-02; v1 results in `results/pit_v1/`):** Gen321 wide carry 0.76 / 0.08 / **-0.13** (was 0.23), v8.4 + it 2.724; Gen326 K = 60 / 100 / 150: 2.650 / 2.725 / 2.500; Gen372 F1 2.318 (was 2.290); Gen374 stress book point-in-time 1.89 / 0.57 / -0.63, expected live 0.42, still dropped. **Gen373 (C\*, K1) unchanged**: the TradFi perps never reached C\*'s 200-day history rule. All conclusions stand.
- **Data gap:** the pushed `research_data/binance_pit` has symbols 0-9 and A-S only (532 crypto coins after the exclusion); T-Z (delisted coins included) are missing, so the point-in-time results are, if anything, still slightly optimistic. Final rerun after the user's next push.

## Gen375 (2026-10-25): K1 prop settings and factors on an established-coin point-in-time universe (`config/gen375_protocol.json`)
- **A, prop settings (27, chosen on 2022-24):** best eligible **challenge 2.0 / funded 2.0 / stop 0.5** (net $185.9k / p10 $93.9k vs current 2.0 / 1.5 / 0.5 $159.6k / $87.2k) -> adopted by the rule. **Flag:** holdout 2025-26 $128.6k / $40.0k / 0.985 vs $119.5k / $53.8k / 0.998, and at planning level (Sharpe 1.37) $70.7k / **$1.2k / 0.905** vs $71.4k / $8.5k / 0.943: no extra money and a worse bad case once the edge is at its realistic size. The funded risk only matters after a pass, so it is set at the paper review: 2.0 only if live evidence supports Sharpe >= 1.8, else 1.5.
- **B, cross-sectional factors on the top-30 by volume among coins listed >= 365 days (delisted included):** premium carry -0.85 / 0.29 / 0.35 (K1 -> 2.369), funding carry -0.66 / 0.20 / -0.07 (2.268), momentum 28d 0.74 / 0.36 / -0.60 (2.297). **All fail.** Honest cross-sectional altcoin factors carry no usable edge in this data.

## Paper v9.0 (2026-10-25): the honest book goes into paper trading (`config/paper_v90.json`, `paper_v90_start.bat`)
- `QPL_PAPER=v90`: Gen373 K1 sleeves; C\* = `CS.cstar_pit_weights()` (point-in-time top-10 by 30-day volume, monthly; live candidates = the 60 pack + extra coins, so a brand-new coin outside them cannot enter). Research-pack _dump: 2.423 [1.104, 3.588, 2.051], corr 0.997 with Gen373 (2.394 incl. delisted candidates, the planning reference); scale 0.885.
- **Selftest PASSED** (15 cutoffs, incl. a month start: max |difference| 1.7e-18). v86 output unchanged after the code changes (max diff 0.0). Runs next to v86 / bf26; paper_report includes it.
- **New data downloader** `get_new_data.bat` (DefiLlama, Blockchain.com, Bybit public BTC/ETH OI and long/short): Gen376 (4 trials) registered before the data exists.

## Gen377 (2026-10-25): K1 robustness, honest BrightFunded book, joint account plan (`config/gen377_protocol.json`, `results/gen377.json`)
- **Deflated Sharpe of K1 (2.394):** DSR 0.994 (N = 300) / 0.976 (N = 1,600): the edge is very likely real. **Planning Sharpe by the project's own method (SR - SR0): 1.07 (N = 300) / 0.84 (N = 1,600).** The 1.37 used since Gen373 scaled v8.6's haircut by a ratio; the haircut is an absolute amount, so a lower backtest Sharpe loses relatively more. **Correction: plan with about 0.85-1.1, not 1.37.**
- Bootstrap 90% interval of the 2022-26 backtest Sharpe: 1.64-3.15.
- **Leave one out:** every sleeve adds except C\* (K1 without C\* 2.402 vs 2.394: better 2022, worse 2023-26; kept, below the +0.05 bar). Biggest contributors: cascade (2.09 without), trend 4h (2.13), Weiss (2.23), delev bounce (2.25).
- **C\* plateau:** top-8 / 10 / 12 give K1 2.364 / 2.394 / 2.409. Not fragile.
- **Honest BrightFunded book (bf2.6 without carry):** 2.301 [0.24, 3.75, 2.14] (bf2.6 2.829), corr 0.82 with K1: mostly the same bet on another platform.
- **Joint account plan (2025-26 days, 730-day bootstrap):**
  - Backtest level: HyroTrader $120k, CFT $117k, BrightFunded $117k, MFP $35k; all four $389k (p10 $171k), outcome corr 0.80.
  - **Planning level (K1 0.84, bf 0.75): per account $25-27k mean, p10 about -$5k, P(profit) 0.70-0.74; all four $85k mean, p10 -$16k, P(total loss) 0.21, P(every account loses) 0.115.**
- Consequence: at an honest planning Sharpe the prop plan is a positive-expectation bet with a real chance of losing the fees. The paper / early-live Sharpe decides how many accounts make sense: start with ONE account; add more only after live results support Sharpe >= 1.5.

## Gen376 / Gen378 (2026-10-25): new free data and venue-divergence ideas (`results/gen376.json`, `results/gen378.json`)
- **Gen376 (registered before the data; perp-DEX volume download failed, N1 uses DEX volume only):** N1 DEX froth -0.41 / -0.21 / 0.34 (K1 -> 2.270); **N2 stablecoin impulse 1.21 / 0.97 / 0.24 (K1 -> 2.446 [1.36, 3.41, 2.08], +0.05 but 2023-24 lower: near-miss)**; N3 BTC fee pressure 0.46 / 0.38 / 0.27 (2.405, +0.01); N4 Bybit crowding 0.02 / 0.52 / 0.47 (2.339). All fail.
- **Gen378:** A funding divergence Bybit-Binance -0.19 / 0.08 / -1.01; **B OI-share divergence -1.77 / -1.26 / -1.20** (consistently wrong sign); C mempool congestion -0.09 / -0.74 / -0.51; D trend 4h on a point-in-time top-10 0.54 / 1.33 / 0.12 (K1 -> 2.328). All fail.
  - B flipped (FLAGGED post hoc, descriptive): only the registered 7-day change works (1.40 / 0.57 / 0.69); 3-day and 14-day changes are negative in two periods; BTC alone -0.63 in 2023-24. **A lucky point, rejected.**

## Gen379 / 379b / 380 (2026-10-25): diversifier baskets of weak BTC/ETH-only signals (`results/gen379*.json`, `results/gen380*.json`)
- **Gen379 (members chosen on full-period signs):** mint shock, Coinbase hourly premium, stablecoin impulse, fee pressure, Bybit crowding. Basket 1.85 / 2.01 / 0.64; K1 + basket **2.536 [1.600, 3.515, 2.079]**: +0.14 but 2023-24 -0.03. **Fails.**
- **Gen379b (FLAGGED follow-up):** weight chosen on 2022-24 = 1.0 -> fails (m = 0.5 would pass, but the rule chose 1.0). Basket robustness: positive every year 2022-26 (1.70 / 1.81 / 2.21 / 0.47 / 0.86), costs x2 1.05, one day / hour later 1.19, leave-one-out 1.13-1.42.
- **Gen380 (walk-forward, members chosen on 2022-24 ONLY from 26 BTC/ETH-only sleeves):** 10 kept (USDT premium, call-minus-put options flow, mint shock, stablecoin impulse, Coinbase hourly premium, attention momentum, FOMC weeks, kimchi BTC/ETH, fee pressure, Bybit crowding). Basket **2.88 / 2.55 / 1.26 (2025-26 out of sample for the selection)**, every calendar year positive (2.88, 1.97, 3.03, 0.94, 1.76), corr K1 0.40.
  - **K1 + basket 2.707 [2.205, 3.438, 2.215]**: +0.31; 2022 +1.15; **2025-26 +0.16 (out-of-sample check passes)**; 2023-24 -0.11 -> **fails the strict rule** (the dilution of K1's unusually strong 2023-24). By calendar year better in 4 of 5 (2023 3.17 vs 3.54).
  - Gen380b (descriptive): deflated planning Sharpe **1.15 vs 0.84**; worst day at risk 2.0 **-6.6% vs -12.9%**; max DD -17.8% vs -20.2%; HyroTrader 2022-24 $163k / $96k vs $160k / $87k; 2025-26 $127k / $55k vs $120k / $54k; at planning level $31.9k / P(profit) 0.77 vs $27.2k / 0.74.
- **Status: v9.1 candidate (K1 + Gen380 basket), FLAGGED:** it fails the pre-registered strict rule in 2023-24 but passes the out-of-sample test and improves the tail; adopting it needs an explicit decision (the strict rule is not silently changed). Live needs feeds for Coinbase USDT-USD, Deribit option trades, DefiLlama, Blockchain.com, Bybit long/short, Google Trends (2-day lag) and the FOMC calendar.
- **2026-10-25: the user ACCEPTED v9.1 = K1 + Gen380 basket** (explicit exception to the strict rule: 2023-24 -0.11, out-of-sample 2025-26 +0.16). **Reference from here: v9.1 2.707 [2.205, 3.438, 2.215], planning 1.15.** Basket enlargements are judged with the strict rule vs v9.1.

## Gen381 (2026-10-25): 10 more BTC/ETH signals for the basket (`results/gen381.json`)
- 2022 / 2023-24 / 2025-26: VIX term structure -0.12 / -0.82 / 0.13; VIX shock 0.74 / -0.90 / 0.18; CME asset managers -0.38 / 0.19 / 0.38; CME leveraged funds -0.75 / -0.40 / -0.23; fear & greed contrarian -0.48 / -0.28 / -0.25; **top-trader crowding 1.56 / 0.88 / 0.32**; taker flow momentum 1.84 / -1.26 / -0.81; network activity -1.04 / -0.94 / -0.43; buy-bitcoin attention -0.61 / 0.57 / 0.04; ethereum attention -0.90 / 0.75 / -0.20.
- Only top-trader crowding enters; the 11-member basket gives K1 2.695 [2.202, 3.423, 2.194] < v9.1 2.707. **Fails; v9.1 unchanged.**

## Gen382 (2026-10-25): how much risk for the basket (`results/gen382.json`)
- Chosen on 2022-24: A the 10 members as separate sleeves (2022-24 3.04) -> **2.711 [2.804, 3.132, 2.178]**; B basket x2 2.707 [2.467, 3.253, 2.232]; C x3 2.640. **Fails** (2023-24 lower; 2022-26 flat): more basket weight moves Sharpe from 2023-24 to 2022 without raising the total. v9.1 unchanged.

## Gen383 (2026-10-25): neighbourhood ensembles in v9.1 (`results/gen383.json`)
- trend 4h ensemble 2.732 [2.249, 3.441, 2.249]; alt kimchi ensemble 2.717; **both 2.743 [2.269, 3.453, 2.255]: every period up but +0.036 < +0.05. Fails** (second time after Gen336 that these ensembles give a small consistent gain; noted as a robustness candidate for the paper review).

## Gen384 / Gen385 (2026-10-25): BTC/ETH positioning signals and the v9.2 candidate (`results/gen384.json`, `results/gen385.json`)
- **Gen384 (6 time-series signals on BTC/ETH):** retail crowding 0.81 / 0.89 / -0.05; top-trader position crowding -0.97 / -0.11 / -0.07; premium discount -0.96 / -0.73 / 0.32; funding contrarian -0.08 / -0.42 / 0.46; **leverage build-up (OI growth, contrarian) 0.67 / 0.65 / 0.04**; spot-led demand -0.84 / 0.80 / -1.42. The rule keeps 12 members (adds top-trader crowding and leverage build-up); basket 3.21 / 2.81 / 1.24 (2.35); K1 + basket 2.739 [2.288, 3.473, 2.208]: +0.032, 2025-26 -0.007. **Fails.**
- **Gen385 (FLAGGED post hoc: Gen383 ensembles + Gen384 basket):** **2.771 [2.342, 3.486, 2.247]: every period up, +0.064 -> passes the strict rule**; by year 2.34 / 3.24 / 3.74 / 1.65 / 2.98 (v9.1 2.20 / 3.17 / 3.72 / 1.51 / 3.08); worst day -7.2%, max DD -17.4%. **v9.2 candidate, needs the user's OK** (post hoc).

## Gen386 (2026-10-25): options-flow, attention and miner signals (`results/gen386.json`)
- 2022 / 2023-24 / 2025-26: put/call contrarian 0.41 / 0.36 / -0.41; block call-minus-put -0.92 / -0.53 / 0.11; short-dated IV inversion -0.04 / -0.36 / -0.89; OTM call froth -0.09 / 0.49 / -0.40; **crypto attention momentum 0.04 / 1.27 / 0.34**; dogecoin froth 0.83 / -0.99 / 0.08; miner revenue momentum -0.67 / 0.37 / -0.07.
- The rule adds put/call and crypto attention (14 members); basket 2.26 (lower than Gen384's 2.35); v9.2 structure + it 2.738 < 2.771. **Fails.** The basket is saturating: weak new members dilute it.

## Gen387 (2026-10-25): prop risk grid for the v9.2 candidate (`results/gen387.json`)
- Planning Sharpe of the v9.2 candidate (N = 1,680): **1.21** (v9.1 1.15, K1 0.84).
- Current 2.0 / 1.5: planning $32.1k / P(profit) 0.735; backtest 2022-24 $184.6k / p10 $116.3k; 2025-26 $130.6k / $57.1k.
- Higher risks (2.5-3.0 challenge, 2.0-2.5 funded) raise backtest 2022-24 dollars but every one lowers the planning-level P(profit) (0.52-0.67) and 2025-26 p10. **No change: 2.0 / 1.5 / 0.5 stays.**
- **2026-10-25: the user ACCEPTED v9.2 = Gen385** (K1 sleeves with trend 4h / alt kimchi neighbourhood ensembles + the 12-member Gen384 basket). **Reference from here: v9.2 2.771 [2.342, 3.486, 2.247], planning 1.21 (N = 1,680).**

## Gen388 (2026-10-25): weighting (`results/gen388.json`)
- A, walk-forward Sharpe-weighted basket: 365 d 2.695, 730 d 2.728 [2.363, 3.441, 2.174] (chosen) -> fails. B, sleeve-weight window: 180 d 2.541, 90 d 2.324 -> fails. **Equal risk over 365 days stays.**

## Gen389 (2026-10-25): multi-timeframe trend (`results/gen389.json`)
- 1h breakout alone and 12h alone are weak (12h 2025-26 0.05); A 1h + 4h + 12h 2.563, B 4h + 12h 2.654 (chosen) -> **fails**. The 4h timeframe stays. (Gold via PAXG perps checked and dropped: perp only since 2025-03, gold trend weak before 2024 in Gen98 / Gen139.)

## Gen390 (2026-10-25): SOL breadth, autocorrelation regime, hash ribbons (`results/gen390.json`)
- 2022 / 2023-24 / 2025-26: top-trader crowding incl. SOL 0.53 / 1.15 / 0.21; retail crowding incl. SOL 0.47 / 1.14 / 0.01; leverage build-up incl. SOL 0.90 / 0.06 / -0.21; autocorrelation regime -1.22 / -0.79 / 0.18; hash ribbons 0.22 / 0.10 / -1.08.
- The loose rule keeps 16 members (incl. hash ribbons, put/call); basket 2.07; book 2.711 < 2.771. **Fails.** Weak members dilute the basket.

## Gen391 (2026-10-25, FLAGGED): forward-stepwise basket selection on 2022-24 (`results/gen391.json`)
- Steps (basket 2022-24 Sharpe): USDT premium 1.53, + mint shock 2.06, + call-minus-put flow 2.35, + kimchi BTC/ETH 2.67, + top-trader crowding 2.83, + leverage build-up 3.02, + stablecoin impulse 3.08, + fee pressure 3.17; stop.
- Basket **3.36 / 3.08 / 1.41** (2025-26 out of sample), 2.54 overall. v9.2 structure + it **2.829 [2.298, 3.598, 2.309]**: +0.058, 2023-24 and 2025-26 up, 2022 -0.044 -> **fails the strict rule by 0.04 in 2022**. By year 2.30 / 3.41 / 3.80 / 1.65 / 3.16. **v9.3 candidate (flagged), for the user's decision.**

## Gen392 (2026-10-25): OI / price divergences on BTC, ETH, SOL (`results/gen392.json`)
- Squeeze fade 1.71 / -0.81 / 0.38 (13 events); trapped shorts -1.53 / -0.44 / 0.40 (13 events); euphoria fade -0.93 / -0.98 / 0.28. **All fail**; the stepwise basket is unchanged.
- **Gen391b (robustness of the v9.3 candidate):** basket positive every year (3.36 / 2.60 / 3.50 / 1.28 / 1.66); leaving out any one of the 8 members keeps the book at 2.757-2.841 (v9.2 2.771). Not driven by one signal.
- **2026-10-25: the user ACCEPTED v9.3 = v9.2 structure with the Gen391 stepwise basket** (flagged: 2022 -0.04). **Reference from here: v9.3 2.829 [2.298, 3.598, 2.309], planning about 1.27.**

## Gen393 (2026-10-25): C* variants in v9.3 (`results/gen393.json`)
- No C\* 2.860 [2.672, 3.601, 2.196] (chosen on 2022-24) -> 2025-26 -0.11, **fails**; C\* BTC/ETH 2.783; C\* BTC/ETH/SOL 2.826. v9.3 unchanged.
- v9.3 leave-one-out (descriptive): without basket 2.442, cascade 2.571, trend 4h 2.655, Weiss 2.691, delev bounce 2.732, alt kimchi 2.736, C\* 2.860, ridge 2.862. C\* and ridge lose in 2022 but carry 2025-26.

## Gen394 (2026-10-25): slower basket members (`results/gen394.json`)
- 3-day smoothing (chosen): basket 3.38 / 2.80 / 1.57, book 2.824 [2.379, 3.536, 2.321]; 7-day: basket 2.92 / 2.78 / 1.78, book 2.778. **Fails** (2023-24 lower, total flat). Slower members are stronger in 2025-26: noted.

## Gen395 (2026-10-25): market-neutral relative crowding among BTC / ETH / SOL (`results/gen395.json`)
- R1 top-trader accounts **1.00 / 0.16 / 0.81** (corr K1 -0.07); R2 retail accounts **1.15 / 0.18 / 0.98** (-0.14); R3 leverage -0.01 / 0.18 / -0.38; R4 funding 0.27 / 1.90 / -0.57; R5 premium 0.07 / 1.86 / -0.59.
- Stepwise adds R4 (2022-24 3.27): book 2.848 [2.232, 3.733, 2.271] -> **fails** (2022 and 2025-26 lower). R1 / R2 are positive in every period but weak in 2023-24, so the 2022-24 stepwise skips them.

## Gen396 (2026-10-25, FLAGGED): relative crowding as a sleeve (`results/gen396.json`)
- 3-coin sleeve 1.30 / 0.17 / 0.91 (by year 1.30, -0.05, 0.46, 1.19, 0.29), corr v9.3 -0.09. v9.3 + it 2.779 [1.730, 3.684, 2.413] -> **fails** (2022 falls while the new sleeve warms up in the risk weights).
- Robustness: BTC/ETH only 1.79 / -0.73 / 0.58; **6 coins (BTC, ETH, SOL, XRP, BNB, DOGE) 1.32 / 1.26 / 1.33**; costs x2 1.20 / -0.03 / 0.63; one day later 0.30 / -0.10 / 0.88; z 60 0.92 / 0.32 / 0.94; z 180 1.13 / 0.49 / 0.62.

## Gen397 / 397b (2026-10-25, FLAGGED): 6-coin relative crowding (`results/gen397*.json`)
- Sleeve (BTC, ETH, SOL, XRP, BNB, DOGE; market neutral; mean of relative top-trader and retail crowding) **1.32 / 1.26 / 1.33**; point-in-time top-6 (pack coins, monthly) version 0.66 / 1.05 / 1.32.
- A in the basket: 2.897 [2.297, 3.715, 2.376]; **B as its own sleeve (chosen on 2022-24): 2.932 [2.246, 3.813, 2.408]**: +0.10, 2022 -0.05 -> fails the strict rule by 0.05 in 2022.
- Gen397b: planning **1.37 vs 1.27**; max DD at risk 2 **-16.1% vs -19.6%**; worst day -8.2% vs -8.0%; HyroTrader 2022-24 $190k / $110k vs $177k / $105k; **2025-26 $162k / $78k vs $141k / $61k**. Book robustness (sleeve variant): costs x2 2.852, one day later 2.863, z 60 2.924, z 180 3.073 (all >= v9.3).
- **v9.4 candidate (v9.3 + 6-coin relative crowding sleeve), flagged: needs the user's OK.**
- **2026-10-25: the user ACCEPTED v9.4 = v9.3 + 6-coin relative crowding sleeve** (flagged: 2022 -0.05). **Reference from here: v9.4 2.932 [2.246, 3.813, 2.408], planning 1.37.**

## Gen398 (2026-10-25): relative crowding extensions (`results/gen398.json`)
- Point-in-time top-10 (pack coins) 0.70 / 1.80 / 0.39, book 2.866; + top-trader positions 0.72 / 1.72 / 0.85, book 2.934 (+0.002); + taker flow contrarian -0.03 / 0.94 / 1.27, book 2.827. **All fail**; the 6-coin two-metric sleeve stays.

## Gen399 / Gen400 (2026-10-25)
- **Gen399 (flagged): relative crowding window ensemble 60 / 90 / 180:** sleeve 1.40 / 1.42 / 1.30, book 2.937 [2.191, 3.843, 2.415] (+0.005, 2022 lower). **Fails**; v9.4 keeps the 90-day sleeve.
- **Gen400: relative kimchi (market neutral):** alts -0.32 / 0.87 / **-2.04** (book 2.683); incl. BTC/ETH -0.39 / 0.83 / -1.92. **Both fail.**

## Gen401 (2026-10-25): relative crowding rebalance frequency (`results/gen401.json`)
- 8-hourly: sleeve **1.45 / 1.84 / 1.21**, book 2.927 [2.348, 3.740, 2.441] (2023-24 lower); 3-day smoothing: sleeve 0.98 / 1.17 / 1.55, book 2.948 [2.271, 3.816, 2.432] (every period up, +0.016). **Both fail** (the sleeve is strong in every form; its book weight caps the gain).

## Gen402 (2026-10-25): relative price signals among the 6 majors (`results/gen402.json`)
- Relative C\* 1.46 / 1.08 / 0.11 (book 2.887); relative 28-day momentum 0.83 / 1.25 / 0.33 (2.833); **relative 7-day reversal -2.18 / -1.94 / -1.36** (2.537). **All fail.** The reversal result says the opposite (short-term relative momentum) holds in every period; with Gen319 B (7-day reversal on 60 coins negative everywhere) -> Gen403.

## Gen403 (2026-10-25, FLAGGED): relative short-term momentum among the 6 majors (`results/gen403.json`)
- Ensemble k = 5 / 7 / 10: **1.27 / 1.24 / -0.09**; book 2.834 [2.204, 3.761, 2.254]. Single k: 3 0.91 / 1.17 / -0.52; 5 1.16 / 1.00 / -0.07; 7 1.68 / 1.30 / 0.30; 10 0.75 / 1.19 / -0.48; 14 0.94 / 1.49 / 0.23; costs x2 0.94 / 0.89 / -0.65; point-in-time top-6 0.38 / 1.55 / -0.04. **Fails**: the effect is gone in 2025-26 and costs take a large share (the strong negative Gen402 reversal was partly its own costs).

## Gen404 (2026-10-25, FLAGGED): relative crowding as the mean of its daily / 8-hourly / 3-day versions (`results/gen404.json`)
- Sleeve **1.48 / 1.55 / 1.46**; book **2.976 [2.355, 3.832, 2.447]**: every period up, +0.044 (< +0.05). **Fails the strict rule by 0.006.** By year 2.35 / 3.50 / 4.17 / 1.98 / 3.04. **v9.5 candidate (robustness upgrade, flagged), for the user's decision.**

## Gen405 (2026-10-25): smart vs retail divergence (`results/gen405.json`)
- Directional BTC/ETH 1.01 / 0.48 / -0.17 (book 2.774); relative 6 coins 1.68 / -0.49 / 0.75 (2.807). **Both fail.**
- **2026-10-25: the user ACCEPTED v9.5 = v9.4 with the Gen404 frequency-ensemble relative crowding sleeve** (flagged: +0.044, every period up). **Reference from here: v9.5 2.976 [2.355, 3.832, 2.447], planning about 1.41.**

## Gen407 (2026-10-25): risk tuning inside relative crowding (`results/gen407.json`)
- Beta-neutral: sleeve 1.07 / 1.27 / 0.67, book 2.802; inverse-vol: sleeve 0.99 / 1.39 / 1.39, book 2.900. **Both fail** (v9.5 rebuilt 2.976 exactly).

## Gen408 (2026-10-25): crowding change (`results/gen408.json`)
- Relative 7-day crowding change: sleeve 1.38 / 0.78 / 0.39 (corr 0.45 with the v9.5 sleeve); as an added sleeve 2.830, mixed with the level 2.915. **Both fail.** (CFD transfer of the futures book for the BrightFunded account not re-tested: 31 earlier CFD ideas failed and bonds are not listed.)

## Gen409 (2026-10-25): directional crowding at 8 hours (`results/gen409.json`)
- Sleeve - / 0.96 / 0.79 (2022 undefined: warm-up), corr v9.5 0.28; book 2.840 [2.355, 3.556, 2.342]. **Fails.** v9.5 unchanged.

## Paper v9.5 (2026-10-26): `config/paper_v95.json`, `paper_v95_start.bat`
- `QPL_PAPER=v95`: K1 sleeves with the trend 4h / alt kimchi ensembles, the Gen391 basket and the Gen404 relative crowding sleeve (`scripts/basket_live.py`).
- The live code reproduces the research sleeves exactly (basket 3.358 / 3.080 / 1.410, corr 1.0; relative crowding max diff 2e-18). Book on the research pack 3.016 [2.428, 3.891, 2.442], corr 0.98 with the research v9.5 2.976 (C\* candidates = the 60 known coins live); scale 0.904. **Selftest PASSED** (15 cutoffs, max |difference| 1.7e-18). v86 output unchanged (max diff 0); v90 sleeves unchanged.
- New live feeds (v95 only): Binance long/short ratios for the 6 coins (`binance_public.update_ratios`, merged in `binance_pack.metrics`), Coinbase USDT-USD, DefiLlama stablecoins, Blockchain.com fees, Deribit option flow (`ml_feeds.update_v95`). Binance serves ratios for the last 30 days only: start the v95 run before about 2026-10-29 to avoid a gap after the research pack (ends 2026-09-30).

## Gen406 (2026-10-26, registered before the data): relative crowding on Bybit (`results/gen406.json`)
- **Y1 Bybit relative crowding (6 coins, account long ratio): 0.31 / 0.43 / 1.62**, corr 0.52 with the Binance sleeve: **the effect replicates on an independent venue** (positive in every period). Y3 Bybit 15 coins: 0.45 / 0.34 / 0.62.
- Books vs v9.5 2.976: Y1 added 2.826; Y2 two-venue mix 2.848; Y3 added 2.959 [2.581, 3.670, 2.466] (2022 +0.23, 2023-24 -0.16). **All fail**; v9.5 unchanged. Value: out-of-venue confirmation of the v9.5 relative crowding sleeve.
- Y4 (Hyperliquid) not run: the download paged only BTC fully (rate limit); the downloader now retries.

## Gen411 (2026-10-26): more relative crowding variants (`results/gen411.json`)
- A relative crowding weight x1.5: 2.959 [2.248, 3.851, 2.471]; B + 4-hourly component (sleeve 0.96 / 1.71 / 0.82): 2.953; C crowding x momentum (sleeve -1.01 / 0.54 / 0.01): 2.070. **All fail**; v9.5 unchanged.

## Gen412 (2026-10-26): intraday timing (`results/gen412.json`)
- Sleeves 2022 / 2023-24 / 2025-26: intraday momentum BTC/ETH 0.72 / -2.05 / -3.94; hour-of-week seasonality -4.58 / -4.45 / -3.07; pre-funding fade (6 majors) -0.72 / -1.40 / -2.30; post-funding rebound -2.94 / -2.13 / -2.24. Books 2.26 / 1.84 / 2.46 / 2.23 vs 2.976. **All fail**: hourly effects are smaller than 5 bp costs.

## Gen413 (2026-10-26, descriptive decision tool): prop sizing of v9.5 at planning-level Sharpe (`results/gen413.json`, `results/gen413b_2022_24.json`, `results/plan_v95b.json`)
- Gen387 only tried HIGHER risk. HyroTrader $200k grid (challenge 1.0-2.5 x funded 0.75-2.0), book shifted to live Sharpe 1.0 / 1.41 / 1.65 and at backtest level.
- **Challenge 1.5 / funded 1.5 beats the current 2.0 / 1.5 at every planning level, on both bootstrap windows:**
  - 2025-26, Sharpe 1.41: mean $53.0k vs $51.8k, p10 **+$0.1k vs -$4.8k**, P(profit) **0.90 vs 0.83**; Sharpe 1.0: $34.8k / 0.78 vs $31.6k / 0.69; Sharpe 1.65: $65.3k / 0.93 vs $66.4k / 0.89.
  - 2022-24, Sharpe 1.41: $73.8k / p10 $11.2k / 0.97 vs $71.3k / -$0.3k / 0.90; Sharpe 1.0: $52.1k / 0.89 vs $47.0k / 0.80.
  - Backtest level: $156k vs $162k (2025-26), $187k vs $192k (2022-24): about -3%.
  - Daily stop 0.4 / 0.5 / 0.6 of the limit: 0.5 stays best.
- Why: at a realistic live Sharpe, a 2.0 challenge burns more re-buys on drawdowns; 1.5 still reaches the 10% / 5% targets within the horizon.
- **Bot default changed: `qpl.bot.rules.Rules.risk_challenge` 2.0 -> 1.5.** Plan: HyroTrader + CFT at planning 1.41 $108k, P(total loss) 0.10 (was $106k / 0.16). Paper ledgers untouched (they report the unit book).

## Gen414 (2026-10-26): watchlist re-tests vs v9.5 (`results/gen414.json`)
- A ridge + positioning features (Gen304 A): ridge sleeve 0.42 / 2.29 / 1.34; book 2.970 [2.472, 3.865, 2.319]. **Fails** (2025-26 lower).
- B CME basis level as a 9th basket member (Gen281): basket 3.45 / 2.64 / 1.76; book 2.979 [2.415, 3.748, 2.503] (+0.003; the like-for-like rebuilt reference is 2.996 because the live basket code differs in the 2020-21 warm-up only). **Fails.**

## Gen415 (2026-10-26, descriptive): funded payout buffer (`results/gen415.json`; engine options `payout_buffer`, `count_open_profit`, defaults off)
- Keeping 1-5% of the account above the start at each payout cuts funded breaches (planning 1.41, 2025-26: 1.57 -> 1.15 per 2 years) and adds 1-4% to the mean at backtest level, but **at planning Sharpe P(profit) and p10 fall** (1.41, 2025-26: buffer 0 $53.0k / p10 $0.1k / 0.90; 3% $53.4k / -$3.6k / 0.865; 2022-24 likewise). **No change: withdraw everything at each payout.**

## Gen417 (2026-10-26): vol forecast for the book's vol targeting (`results/gen417.json`)
- Replica of portfolio_v5 exact (2.976). EWMA (halflife 10) 2.883; HAR mix (7 / 30 / 90 days) 2.899; hourly realised vol (10 days) 2.806. **All fail**; the 30-day std stays.

## Gen416 (2026-10-26, descriptive): crypto-perp firms for v9.5 at planning Sharpe 1.41 (`results/gen416.json`)
Sizing per firm chosen on the 2022-24 bootstrap (highest mean with P(profit) within 0.02 of the best), reported on 2025-26 (300 paths, stop 0.5 x the daily limit).

| Firm | Fee | Chosen | 2025-26 mean / p10 / P(profit) | per $100k |
|---|---|---|---|---|
| HyroTrader 2-Step $200k | $969 | 1.5 / 1.5 | $51.8k / +$0.5k / 0.90 | $25.9k |
| HyroTrader 2-Step $100k | $579 | 1.5 / 1.5 | $25.6k / -$0.1k / 0.90 | $25.6k |
| CFT 2-Phase $100k | $660 | 1.5 / 1.5 | $26.8k / -$1.4k / 0.85 | $26.8k |
| CFT 2-Phase + weekly + 90% | $924 | 1.5 / 0.75 | $17.7k / +$1.5k / 0.91 | $17.7k |
| HyroTrader 1-Step $100k | $749 | 1.0 / 1.5 | $17.7k / -$2.6k / 0.83 | $17.7k |
| MyFundedPerps $100k | $696 | **1.0 / 1.0** | **$16.6k / -$1.1k / 0.87** | $16.6k |
| Breakout 1-Step Classic | $999 | 1.0 / 1.0 | $14.9k / -$3.9k / 0.81 | $14.9k |
| SizeProp 1-Step | $899 | 1.0 / 0.75 | $10.7k / -$3.1k / 0.82 | $10.7k |
| HyroTrader Zero-Step | $949 | 1.0 / 0.75 | $10.6k / -$3.4k / 0.81 | $10.6k |
| Breakout 2-Step | $999 | 1.0 / 1.0 | $8.9k / -$5.0k / 0.70 | $8.9k |
| CFT 1-Phase | $798 | 0.75 / 1.0 | $5.0k / -$4.0k / 0.59 | $5.0k |
| SizeProp Degen | $522 | 0.75 / 0.75 | $5.0k / -$2.6k / 0.65 | $5.0k |

- **Two-step accounts with a 10% max loss (HyroTrader, CFT) are clearly best at a realistic Sharpe**; one-step / zero-step / tight-drawdown accounts lose most of the edge to breaches.
- **MyFundedPerps re-sized: 1.0 / 1.0 with a 50% daily stop gives $16.6k / P(profit) 0.87, vs $10.9k / 0.67 at the old 1.0 / 2.0 / 40%.**

## Gen418 (2026-10-26, descriptive): what live Sharpe does a prop account need? (`results/gen418.json`)
HyroTrader $200k, challenge 1.5 / funded 1.5 / stop 0.5, v9.5 shifted to each live Sharpe; 2 years; 2025-26 window (2022-24 in brackets).

| Live Sharpe | Mean net | Bad case p10 | P(profit) | P(funded) |
|---|---|---|---|---|
| 0.5 | $19k ($33k) | -$5k | 0.62 (0.77) | 0.80 |
| 1.0 | $35k ($52k) | -$5k (-$2k) | 0.78 (0.89) | 0.90 |
| 1.25 | $46k ($64k) | -$5k (+$7k) | 0.86 (0.95) | 0.95 |
| 1.5 | $57k ($79k) | +$0.5k (+$13k) | 0.90 (0.97) | 0.96 |
| 1.75 | $72k ($95k) | +$11k (+$27k) | 0.95 (0.99) | 0.99 |
| 2.0 | $87k ($112k) | +$19k (+$43k) | 0.97 (0.995) | 0.99 |
| 2.5 | $121k ($149k) | +$48k (+$70k) | 0.995 | 1.00 |
| 3.0 | $158k ($189k) | +$81k (+$111k) | 1.00 | 1.00 |

- The chance of profit saturates (0.97 at 2.0, 0.995 at 2.5); **the money does not**: mean net rises about $30k per +0.5 Sharpe all the way up (and more if risk is raised at higher Sharpe).
- Thresholds: about 1.0 is the minimum worth trading (positive expectation, P(profit) 0.78); about 1.5 makes the bad case break even; about 2.0 makes a loss rare.

## Gen419 (2026-10-26): relative positioning among the 6 majors (`results/gen419.json`)
- Sleeves 2022 / 2023-24 / 2025-26: relative funding 0.28 / 0.62 / -0.55 (book 2.904); relative leverage build-up (contrarian) -1.54 / 0.08 / -1.58 (2.698); relative premium -0.78 / -0.13 / -0.31 (2.775). **All fail.**

## Gen420 (2026-10-26, FLAGGED post hoc): relative OI momentum (Gen419 B reversed) (`results/gen420.json`)
- Sleeve 1.22 / -0.66 / 0.65 (2023 -0.50, 2024 -0.81); book 2.856 [2.523, 3.544, 2.398]. Costs x2 1.06 / -0.95 / 0.19. **Fails**; the Gen419 B loss was not a clean mirror edge.

## Gen421 (2026-10-26): COIN-M positioning, new data (`research_data/binance_cm`, `results/gen421.json`)
- Binance COIN-M BTCUSD_PERP / ETHUSD_PERP metrics 2021-07..2026-09 (public archive; ratio columns only exist since about 2025).
- A COIN-M leverage build-up member 0.07 / 0.27 / -0.27, book 3.005 [2.340, 3.913, 2.434] (2022 and 2025-26 lower). B follow COIN-M vs USDT-M taker divergence -2.82 / -0.20 / -1.72, book 2.875. **Both fail.**

## Gen422 (2026-10-26, FLAGGED post hoc): fade the COIN-M taker divergence (`results/gen422.json`)
- Member 2.24 / -0.69 / 0.82 (2023 -0.23, 2024 -1.03, 2026 -1.44); book 2.989 [2.530, 3.778, 2.453]. **One day later -> 0.19 / -1.17 / -0.64: fragile. Fails.**

## Gen423 (2026-10-26): order-book depth imbalance, new data (`research_data/binance_depth`, `results/gen423.json`)
- Binance USDT-M bookDepth 30-second snapshots 2023-01..2026-09, 6 majors, aggregated hourly (`qpl.lab.binance_depth`).
- A depth imbalance member BTC/ETH: - / -1.41 / 0.87, book 2.962. B relative depth imbalance 6: - / -1.69 / -1.66, book 2.582. **Both fail.**

## Gen424 (2026-10-26, FLAGGED post hoc): fade relative depth imbalance (`results/gen424.json`)
- Sleeve - / 0.41 / -0.05 (costs eat the mirror image); book 2.881. Costs x2 - / -0.23 / -0.90. **Fails.**

## Gen425 (2026-10-26): short newly listed Binance perps (`results/gen425.json`)
- 492 listings 2021-06..2026-09 in `binance_pit` (symbols A..S; first-day volume >= $10M; TradFi excluded). **Median 30-day return after listing is negative in every year** (2021 -23%, 2022 -30%, 2023 -12%, 2024 -10%, 2025 -24%, 2026 -17%), but the means are near zero (a few huge squeezes).
- Short 0.05 per event, gross cap 0.5, 10 bp, funding: hold 30 d sleeve 1.30 / -0.25 / -0.18, book 3.108 [2.758, 3.994, 2.368]; hold 7 d 0.87 / -0.11 / -0.17, book 3.011. **Both fail** (2025-26 lower): the squeezes and funding eat the median edge.

## Gen426 (2026-10-26, FLAGGED post hoc): listing short with a 30% per-event stop (`results/gen426.json`, `gen426b.json`, `gen426c.json`)
- **Sleeve 1.63 / -0.24 / 0.44 (by year 1.63 / -0.68 / 0.14 / 0.55 / 0.22), corr with the book -0.21. Book 3.161 [2.775, 3.919, 2.576]: +0.185, every period up -> passes the strict rule, but the stop was added after seeing Gen425.**
- Robustness (same shape everywhere): stop 20% 1.68 / -0.36 / 0.75; stop 50% 1.79 / -0.23 / 0.21; costs x2 1.61 / -0.27 / 0.40; first-day volume >= $50M 0.90 / -0.16 / 0.46; hold 14 d 1.47 / -0.28 / 0.47; hold 60 d 1.95 / -0.29 / 0.28.
- **Not just short altcoin beta (Gen426b):** hedged with its full-sample beta to the 5 major alts the sleeve is 0.20 / 0.70 / 0.50 (positive every period); a plain alt short with the same beta adds nothing (book 2.995, 2023-24 lower); the beta-hedged listing short still gives 3.073.
- **Gen426c:** planning Sharpe (N = 1,800) **1.41 -> 1.59**; max DD at risk 2 -16.5% -> -14.0%; worst day -8.2% -> -7.3%. HyroTrader 1.5 / 1.5 at planning: 2025-26 $53.0k / p10 $0.1k / 0.90 -> $52.7k / **$3.2k / 0.92**; 2022-24 $73.7k / $11.2k / 0.97 -> **$93.0k / $29.7k / 0.99**.
- Practical: at risk 1.5 the per-coin notional is median 1.0%, max 4.2% of the balance, under HyroTrader's 5% cap for low-cap / Innovation Zone coins (official FAQ). Live needs a listing feed (exchange instrument list) and the coin to be listed on Bybit.
- **v9.6 candidate (flagged), for the user's decision.** Caveat: symbols T..Z are not yet in the data (alphabetical, not performance-based).
- **2026-10-26: the user ACCEPTED v9.6 = v9.5 + the Gen426 listing short** (flagged: post-hoc stop). **Reference from here: v9.6 3.161 [2.775, 3.919, 2.576], planning about 1.59 (N = 1,800).**

## Paper v9.6 (2026-10-26): `config/paper_v96.json`, `paper_v96_start.bat`
- `QPL_PAPER=v96`: v9.5 + listing short (`scripts/listing_live.py`; live feed `binance_public.update_listings`: perps with exchangeInfo onboardDate in the last 45 days, hourly closes + funding).
- Live module timing = the framework's (position in [t, t+1h) from closes known at t; stop and entry one hour after the triggering close, as in Gen426; a coin with a missing latest bar is flat). On the research data: book 3.169 [2.751, 3.949, 2.579] (Gen426 3.161; its script booked each hourly return one bar late, daily corr 0.95). Paper code on the research pack 3.191 [2.746, 3.998, 2.582], corr 0.977 with research v9.6; scale 0.90.
- Bot (dry-run) now reads the v96 book; `Rules.lowcap_cap_frac` 0.05 caps listing-short coins (HyroTrader low-cap rule).
- **Paper v9.6 selftest PASSED** (24 cutoffs incl. a listing entry and a 30% stop, max |difference| 1.7e-18). v95 paper output unchanged (max diff 0 vs `cache_v95_final`).
- Note: the paper v9.6 wiring (paper_v5.py, binance_public.update_listings, bot cap, launchers' config) went into commit "Gen427: judge as registered ..." together with that one-line change, plus the following "Paper v9.6" commit.

## Gen427 (2026-10-26): short after a later Binance spot listing (`results/gen427.json`)
- 31 events (spot listing >= 3 days after the perp; 2023 2, 2024 2, 2025 19, 2026 8). Own sleeve - / -2.08 / -1.02, book 2.994; merged into the listing short 1.51 / -0.29 / 0.19, book 3.145. **Both fail** vs v9.6 3.161 (live-timing reference 3.169). A spot listing after the perp is not a second sell event.

## Gen428 (2026-10-26): listing-short refinements (`results/gen428.json`)
- A inverse-vol sizing: sleeve 1.60 / -0.23 / 0.66, book 3.204 [2.715, 3.976, 2.651] (+0.043, 2022 lower). B skip crowded shorts (150 of 492 events): book 3.119. **Both fail**; the v9.6 listing short stays.

## Gen429 (2026-10-26): fade the crowded side after Binance shortens a perp's funding interval (`results/gen429.json`, robustness `gen429b.json`)
- 234 events (199 long = shorts crowded, 35 short), almost all 2025-26. A hold 7 d: sleeve 0.01 / 0.42 / 1.97 (2023 0.68, 2024 -0.25, 2025 3.31, 2026 0.66), book **3.444 [2.751, 3.941, 3.274]**: +0.28 but 2022 below the research reference (sleeve flat in 2022; equal to the live-timing reference) and 2023-24 -0.008 vs the live-timing reference. B hold 3 d: book 3.262. **Both fail as registered.**
- Gen429b: **top 5 coins = 64% of the P&L (ALPACA, the 2025 delisting squeeze, about 28%); without them 2025-26 falls to 0.79**; long events by year 2023 9, 2024 1, 2025 68, 2026 118. Costs x2 / 1 h later / stop 50% similar; stop 20% 2023-24 -0.71.
- **Not flagged**: a 2025 squeeze regime carried by a few coins, not a stable edge. Watchlist: re-check once the T..Z symbols and more live months exist.

## Gen430 (2026-10-26, descriptive): HyroTrader sizing grid for v9.6 (`results/gen430.json`)
- At planning 1.59: 2025-26 **1.5 / 1.5 $52.6k / p10 +$3.2k / P(profit) 0.92** (best mean of 16 cells; 2.0 / 1.5 $48.9k / 0.83); 2022-24 1.5 / 1.5 $93.0k / +$29.7k / 0.99 (2.0 / 2.0 $96.6k but p10 $14.4k / 0.95). At a weak 1.2 1.5 / 1.5 is best on both windows. Only at backtest level does more risk pay (2.0 / 2.0 $175k / $265k).
- **No change: challenge 1.5 / funded 1.5 / stop 50% stays for v9.6.**

## Gen433 (2026-10-26): C* in v9.6 (`results/gen433.json`)
- Without C*: 3.112 [3.129, 3.730, 2.450]; C* at half weight: 3.176 [2.926, 3.892, 2.560]. **Both fail** (2023-24 and 2025-26 lower); C* stays at full weight.

## Gen432 (2026-10-26, descriptive): the listing effect on OKX (`research_data/okx_listings`, `results/gen432.json`)
- 425 OKX USDT-swap listings 2021-06..2026-09 with 25+ days of data (92 also Binance listing events within 7 days). **Only currently listed swaps are served (delisted ones are missing): for older listings this biases strongly AGAINST the short.**
- Median 30-day return by year: 2021 +10%, 2022 -14%, 2023 -4%, 2024 +2%, **2025 -37%**, 2026 -5%; Gen426 rule per event before funding: -13% / -11% / -6% / -8% / **+18%** / +4%. OKX-only events: median -7%, rule +3%.
- **Reading:** strong confirmation in 2025, consistent sign in 2022 and 2026; 2021-24 not confirmed (survivor-only data, no volume filter). A caution flag on v9.6's listing short: the edge is clearest in 2025, and its 2023-24 contribution was already slightly negative on Binance. Live paper results decide; no change.

## Gen434 (2026-10-26): pace of new listings as a froth signal (`results/gen434.json`)
- A BTC/ETH basket member 0.17 / -1.11 / -0.27, book 3.126; B alt short sleeve -0.07 / -1.32 / -0.31, book 2.961. **Both fail.**

## Gen435 (2026-10-26): the futures book as a sleeve via TradFi perps (`results/gen435.json`)
- Futures book (minus a 4% a year perp funding drag): 0.76 / 0.57 / 0.49, daily corr with v9.6 0.01; book 3.160 [2.763, 3.934, 2.568]. **Fails**: an uncorrelated Sharpe-0.5 sleeve cannot move a 3.2 book (the ceiling is about sqrt(3.16^2 + 0.6^2) = 3.22 even at the optimal weight).

## Gen437 (2026-10-26, descriptive): two accounts, second one started later (`results/gen437.json`)
- Two HyroTrader $200k accounts on v9.6 (1.5 / 1.5), same bootstrap paths, each trading 2 years. 2025-26 at planning 1.59: together $101.6k / p10 -$1.2k / P(total loss) 0.102; second +90 d $102.1k / +$4.5k / 0.075; **second +180 d $101.9k / +$9.9k / 0.062**. At a weak 1.2: P(total loss) 0.195 -> 0.150 -> 0.125. 2022-24 the same direction.
- **Plan: open the second account 3-6 months after the first** (same mean, clearly better bad case; it also fits "add the second only after live results").

## Gen438 (2026-10-26): shrunk-Sharpe sleeve weights at the top level (`results/gen438.json`)
- Equal-risk replica 3.169 (= v9.6 live timing). A 730-day shrunk Sharpe 3.025 [2.62, 3.801, 2.397] ; B expanding 3.026 [2.647, 3.74, 2.455]. **Both fail**: past sleeve Sharpe does not predict; equal risk stays (third time, after Gen156 / Gen388).

## Gen439 (2026-10-26): market-wide altcoin froth, contrarian (`results/gen439.json`)
- Point-in-time top-100 perps (pack + extra + pit A..S), volume-weighted. A funding froth member -1.16 / -0.77 / -0.08, book 3.157; B premium froth -0.67 / -0.85 / -0.75, book 3.144. **Both fail** (contrarian loses everywhere).

## Gen440 (2026-10-26, FLAGGED post hoc): follow the market-wide alt premium (`results/gen440.json`)
- Member **0.65 / 0.81 / 0.69, every year positive (0.65 / 0.99 / 0.74 / 0.03 / 1.20), corr BTC -0.05; robust** (costs x2 0.64 / 0.79 / 0.67; 1 day later 0.71 / 0.83 / 0.74; smoothing 3 / 14 and top-50 / 200 similar).
- As a 10th basket member: basket 3.22 / 2.78 / 1.54, book 3.147 [2.623, 3.952, 2.602] < 3.169. **Fails** (dilutes the stronger members). Kept on the list of robust candidates for a structured basket re-selection.

## Gen441 (2026-10-26): Gen391 stepwise basket re-selection with the newer candidates (`results/gen441.json`)
- Pool + Gen440 follow froth, Gen281 CME basis, Gen421 A COIN-M leverage, Gen434 A listing pace. **The procedure picks exactly the same 8 members** (basket 3.36 / 3.08 / 1.41); no change. The current basket is stable against new candidates.

## Gen436 (2026-10-26): v9.6 on the complete point-in-time universe A..Z (`results/gen436.json`)
- T..Z (135 perps) fetched in the cloud from data.binance.vision; binance_pit now 840 perps. **583 listing events (90 in T..Z).**
- Listing short sleeve **1.67 / -0.13 / 0.73** (by year 1.67 / -0.54 / 0.19 / 0.94 / 0.28; A..S was 1.51 / -0.23 / 0.43). **Book v9.6 3.212 [2.748, 3.969, 2.664]** (A..S live timing 3.169). Planning (N = 1,800) **1.64** (A..S 1.59).
- **Correction (same day): `config/tradfi_perps.json` lists base names (AAPL, XAU) but the listing scripts compared full symbols (AAPLUSDT), so 33 TradFi listings (all 2026) were NOT excluded in Gen425-436 and in `listing_live.py`. Fixed everywhere (also Gen410 / 429 / 434 / 439 scripts). Corrected A..Z: 550 events, sleeve 1.67 / -0.13 / 0.61 (2026 -0.24), book 3.203 [2.748, 3.969, 2.642], planning 1.64 (N = 1,800).**
- **Decision rule: v9.6 stands.** Reference from here: v9.6 A..Z (TradFi excluded) 3.203 [2.748, 3.969, 2.642], planning about 1.64. The running paper v96 reads the same files (code unchanged; history now includes T..Z).
- **Gen429 re-check on A..Z (TradFi excluded; 2026-10-26):** 239 events; A hold 7 d sleeve 0.01 / 0.40 / 1.81, book 3.355 [2.748, 3.945, 3.019] vs v9.6 A..Z 3.203 [2.748, 3.969, 2.642]: still fails (2023-24 -0.024); top 5 coins 58% of the P&L, without them 2025-26 0.84. **Still watchlist, not flagged** (A..S results kept in `results/gen429_AS.json`, `gen429b_AS.json`).

## Gen442 (2026-10-26): fade non-listing pumps on mid caps (`results/gen442.json`)
- Ranks 21-150 (A..Z, TradFi excluded), +40% in 24 h on 5x volume, short 0.05 with a 30% stop. A hold 7 d: 0.06 / 0.01 / -0.38 (2023 2.42, 2024 -1.42), book 3.064; B hold 3 d: 0.22 / 0.27 / 0.21, book 3.089 (2025-26 2.198). **Both fail.** Mid-cap pumps do not fade reliably either; only the listing effect holds.

## Gen443 (2026-10-26): listing short entered 6 h after listing (`results/gen443.json`)
- Sleeve 1.34 / -0.05 / 0.70 (2026 -0.55), book 3.206 [2.556, 3.969->4.035, 2.693]: 2022 lower (2.556 < 2.748). Costs x2 3.195. **Fails**; the entry at the first midnight >= 24 h stays.

## Diagnostic (2026-10-26): where v9.6 loses
- Monthly hit rate 0.77 (57 months); **monthly corr with BTC 0.43**; worst months 2025-12 -5.8% (trend 4h, relative crowding, basket), 2026-07 -4.0% (ridge, C*), 2023-04 -3.8% (relative crowding). No single sleeve dominates the losses; the book still carries market beta in bad months. Target for research: an edge that pays in falling markets without being a plain short.

## Gen444 (2026-10-26): Hyperliquid funding across the 6 majors (`research_data/hyperliquid`, `results/gen444.json`)
- Hyperliquid hourly funding 2023-05..2026-10 fetched in the cloud (15 coins). A (Gen406 Y4) relative HL funding contrarian: - / -0.70 / 0.31, book 3.003; B HL-minus-Binance funding spread relative: - / -0.87 / 0.46, book 2.887. **Both fail** (2024 strongly negative).

## Gen448 (2026-10-26): Weiss expiry at full weight (`results/gen448.json`)
- Book 3.259 [2.797, 4.081, 2.624] vs v9.6 A..Z 3.203 [2.748, 3.969, 2.642]: +0.056, 2022 and 2023-24 up, **2025-26 -0.018 -> fails (near miss)**. Half weight stays.
- **Gen436b (descriptive, `results/gen436b.json`): v9.6 listing-short robustness.** Costs 10 / 20 / 30 bp per side: book 3.203 / 3.193 / 3.184; entry one day later 3.179 [2.697, 3.971, 2.605]. Robust to execution (v9.5 2.976).
- **Paper v96 selftest re-run after the TradFi fix: PASSED** (24 cutoffs, max |difference| 1.7e-18).
