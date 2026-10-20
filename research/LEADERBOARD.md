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
