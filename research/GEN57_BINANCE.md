# Gen57 / Gen60 (Binance part): tests on the user's Binance futures pack (2026-10-15)

**Data:** 20 USD-M perps, 2020-01 to 2026-09:
- 5-minute klines with taker volume;
- open interest and long/short ratios from 2021-12;
- 8h funding;
- hourly premium index.

**Rules:** written down before the data arrived (`config/gen57_protocol.json`, `config/gen60_paper_scan_queue.json`).

**Scripts:** `scripts/gen57_*.py`. Results: `results/gen57_*.csv`.

**Periods:** DEV = 2020–22, TEST = 2023–24, HOLD = 2025–26, "2023+" = TEST + HOLD.

## 1. C* + BTC leads on real perp prices with real funding (T9, T10)

Sharpe:

| Variant | 2020–26 | DEV | 2023+ |
|---|---|---|---|
| Spot backtest (reference) | 2.01 | 2.40 | 1.67 |
| Perp prices, no funding | 1.95 | 2.29 | 1.66 |
| **Perp + real funding (00:00 UTC)** | **1.75** | 2.00 | **1.55** |
| Perp + funding, rebalance 08:00 UTC | 1.73 | 2.04 | 1.48 |
| T10a crowding filter | 1.77 | 2.00 | 1.56 |
| T10b taker confirmation | 1.63 | 2.01 | 1.35 |
| T10c wick guard (-3 ATR stop) | 1.50 | 1.73 | 1.32 |

- **Funding costs C\* 3.1% of equity a year.** Average funding on the 10 majors is 12–14% a year, paid by longs. From now on, the realistic C\* figure on perps is about 1.55 in 2023+.
- **Rebalancing at 08:00 UTC instead of 00:00 costs about 0.07 Sharpe**, and the worst day goes from -5.5% to -8%. 00:00 stays the default; 08:00 is acceptable if the night-time rebalance is impractical.
- **No overlay passes the pre-registered +0.10 Sharpe bar.** The crowding filter reached +0.01.

## 2. New crypto strategies

| Test | DEV | TEST | HOLD | 2023+ | corr C* | Verdict |
|---|---|---|---|---|---|---|
| T1 BTC 21–23 UTC long, taker | -0.38 | -0.38 | -1.76 | -0.96 | 0.13 | rejected |
| T1 BTC 21–23 UTC, maker (5-min fill approximation) | 0.60 | 0.94 | -0.24 | 0.44 | 0.13 | rejected |
| **T1 ETH 21–23 UTC, maker** | 0.51 | 1.25 | 0.76 | **0.99** | 0.15 | **near-miss** (depends on maker fills; BTC, the primary, fails) |
| B2 long 21–23 / short 01–05 UTC | -0.39 | -1.96 | -3.10 | -2.46 | -0.07 | rejected |
| B1 noise-area intraday trend, BTC+ETH | -1.45 | -2.33 | -1.70 | -2.00 | 0.07 | rejected |
| T6 premium-bound reversion, 20 coins | -0.14 | 0.28 | -0.27 | 0.00 | -0.21 | rejected |
| T8 Gao first-to-last half hour | -3.8 | -7.1 | -8.4 | | | rejected |
| T7 Wen hour pairs (Binance) | -4.9 | -6.9 | -9.0 | | | rejected (confirms Gen56) |
| T2 funding carry XS, 7d average, hold 1d | 1.42 | 0.66 | 0.68 | 0.67 | -0.11 | near-miss |
| T2 funding carry XS, 7d average, hold 7d | 1.18 | 0.35 | 1.22 | 0.75 | -0.09 | near-miss |
| T3a contrarian top-trader L/S | 0.56 | -0.67 | -0.41 | -0.56 | | rejected |
| T3b contrarian OI x price | -2.06 | -1.41 | -1.35 | -1.38 | | rejected |
| T8 XS momentum with taker filter | 1.01 | 0.95 | -0.98 | -0.02 | | rejected |
| B3 CTREND-style elastic net | the elastic net shrinks every coefficient to 0; OLS out-of-sample 0.11 | | | | | rejected |
| **B4 liquidation-cascade buy, 12h** | -0.51 (2022 only) | **1.55** | **0.91** | **1.29** | 0.19 | **promising, not validated** |
| B5 opening-bar taker flow | | -3.48 | -1.67 | | | rejected |

### B4 liquidation-cascade reversal

**The rule:** a 1h return below -3σ, open interest down more than 5%, and volume above the 95th percentile. Buy, stop at the cascade low minus 1 ATR, exit after 12h.

**Robustness:**
- **Breadth:** 2,034 events. All 20 coins have a positive mean trade in 2023+.
- **Costs and timing:** 2x costs gives 1.14 (2023+). A 1-hour delay gives 1.71. Thresholds k = 2.5 / 3.5 give 1.28 / 1.10.
- **Long side only works:** the long-only version gives 1.32. Fading squeezes (the short side) loses.

**Weaknesses:**
- **It lost money in 2022** (bear market; mean trade -0.41%). It is a "buy the crash in a bull market" trade.
- **Uncapped, many coins cascade on the same day.** The worst day is -19% at 0.2 notional per event; that has to be capped.
- **It loses on the same crash days as C\*.** Its mean on C\*'s 20 worst days is -3.6%, which fails the pre-registered tail criterion.

**Exploratory (2 extra trials):**
- Capped at 3 open events: 2023+ Sharpe 0.96, worst day -5.7%.
- Plus a BTC-bull-only filter: 0.98.

**Status:** forward-test candidate. Not validated.

## 3. Descriptive combination (2023+, equal risk, nothing optimised)

| Portfolio | Sharpe | Positive months | Worst month | Max DD |
|---|---|---|---|---|
| C* alone (perps + funding) | 1.55 | 44% | -2.3% | -9.5% |
| C* + funding carry | 1.73 | 64% | -1.2% | -5.1% |
| C* + cascade + carry | 1.77 | 69% | -1.4% | -5.8% |
| C* + cascade + ETH evening + carry | **1.98** | **73%** | -1.3% | -4.9% |

All sleeves are scaled to 10% vol. Correlations with C* run from -0.18 (carry) to +0.23 (cascade).

This is the improvement in consistency we are looking for, but it is **descriptive and optimistic**:
- The three add-ons are near-misses, picked out of many tests on the same 2023+ period.
- None passed every pre-registered criterion.

**Next step:** forward-test them in paper trading alongside C*. A sleeve is promoted only if it holds up out of sample. Gen58 shows what such a portfolio would mean at prop firms.

## Trials

About 45 new configurations in total: 37 pre-registered, 2 exploratory cascade variants, and the combination, which is descriptive.
