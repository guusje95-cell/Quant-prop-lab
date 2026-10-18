# Crypto prop-firm portfolio "v5": strategies and results

All figures are backtests on Binance USD-M perpetual futures, Jan 2022 to Sep 2026. They are after trading fees, slippage assumptions and real funding payments, and the portfolio is scaled to 15% annual volatility. Every strategy was written down (pre-registered) before it was tested, with fixed data splits: development 2020-22, test 2023-24, holdout 2025-26.

## The 5 strategies

1. **C\* + BTC leads (crypto trend, long only).**
   - **Coins:** 10 large coins (BTC, ETH, BNB, XRP, ADA, SOL, DOGE, AVAX, DOT, LINK).
   - **Signal:** the average of 15 short breakout rules (new 5-20 day high, hold 1-3 days) and 4 time-series momentum rules (14-90 days).
   - **Stablecoin filter:** exposure x1.25 when USDT+USDC supply grew over 30 days, x0.75 when it shrank.
   - **BTC leads:** altcoins are held only while BTC's own signal is positive.
   - **Execution:** volatility-scaled, rebalanced daily at 00:00 UTC.
2. **Premium carry (market-neutral).**
   - **Ranking:** 20 perpetuals, ranked by their 7-day average premium index (perp price vs spot index).
   - **Positions:** long the lowest third, short the highest third, rebalanced weekly.
   - **Earns:** funding plus convergence of the premium.
3. **Liquidation-cascade buy (hourly).**
   - **Signal:** an hour where all three hold: the return is below -3 sigma, open interest drops more than 5%, and volume is above its 95th percentile.
   - **Entry:** a limit buy 0.5% below that close, valid 1 hour. It counts as filled only if the price trades 0.1% through the limit.
   - **Exit:** stop at the signal bar's low minus 1 ATR; otherwise exit after 12 hours.
   - **Size:** at most 3 trades open, 0.2x notional each.
4. **4-hour breakout trend.**
   - **Coins:** BTC, ETH, SOL.
   - **Rule:** long above the 20-bar high, short below the 20-bar low; exit on a 10-bar opposite break.
   - **Size:** 10% volatility target per coin.
5. **Option-expiry reversal (Weiss et al., 2026).**
   - **When:** the last Friday of each month (Deribit monthly expiry at 08:00 UTC).
   - **Trade:** at 08:00, take the opposite direction of BTC's and ETH's 07:00-08:00 move, and close at 10:00.
   - **Weight:** half, because the evidence is thinnest (81 events, t = 1.6).

**Portfolio construction.**
- **Weights:** each strategy is sized to equal risk using only its past 365 days of volatility, recomputed monthly. There is no look-ahead.
- **Portfolio vol targeting:** 30-day trailing volatility, capped at 1.5x.
- **Prop accounts:** a daily stop goes flat for the rest of the day at 50% of the firm's daily loss limit.

## Results 2022-01 to 2026-09 (portfolio at 15% vol)

| | Portfolio v5 | C\* | Premium carry | Cascade | 4h trend | Expiry reversal |
|---|---|---|---|---|---|---|
| Sharpe | **2.25** | 1.28 | 0.71 | 1.20 | 0.85 | 1.11 |
| Sortino | **4.33** | 2.03 | 1.04 | 2.52 | 1.45 | 2.25 |
| CAGR (at 15% vol) | **38.7%** | 19.9% | 10.0% | 18.4% | 12.3% | 16.9% |
| Max drawdown | **-9.5%** | -15.7% | -16.9% | -16.6% | -15.0% | -15.9% |
| Calmar | **4.08** | 1.27 | 0.59 | 1.11 | 0.82 | 1.06 |
| Positive months | **72%** | 42% | 65% | 53% | 53% | 68% |
| Worst month / worst day | -4.2% / -3.6% | | | | | |
| Longest drawdown | 172 days | | | | | |

- **Strategy columns:** each strategy is shown on its own, scaled to 15% vol.
- **Years:** 2022 +18.8% (crypto bear market), 2023 +63.3%, 2024 +64.0%, 2025 +10.6% (weak year), 2026 Jan-Sep +34.2%.
- **Correlations:** the highest pairwise daily correlation is C\* / 4h trend at 0.33; all other pairs are between -0.07 and +0.19.

## Prop-firm simulation

$100k account, 2 years, block bootstrap with 500 paths. Risk 1.0x in the challenge and 0.6x once funded.

| Firm | Pass rate | Mean net profit | Unlucky 10% | P(profit) |
|---|---|---|---|---|
| HyroTrader 1-Step | 87% | $26.4k | $12.0k | 99.6% |
| HyroTrader 2-Step | 99.8% | $23.9k | $9.9k | 98% |
| SizeProp 1-Step | 78% | $24.2k | $9.0k | 98% |
| Crypto Fund Trader 1-Phase | 65% | $21.8k | $5.9k | 97% |

**At CFD firms (FTMO type).** Only C\* and the expiry reversal survive CFD spreads and swaps:
- Sharpe 1.50;
- mean net about $14-15k per $100k over 2 years;
- P(profit) about 90%.

## Process and honest caveats

- **What was tested:** 75+ research generations and several hundred pre-registered configurations, with trials counted.
- **What was rejected:** most ideas, including:
  - CTREND;
  - AdaptiveTrend;
  - own-history factor books;
  - minute-level lead-lag;
  - 19 index / gold / FX timing ideas on CFD data.
- **Tuning:** re-tuning the strategy parameters on past data made all three tested strategies worse out of sample, so the original settings are kept.
- **Selection bias:** the set of strategies was chosen after seeing 2022-26. The 2.25 Sharpe is therefore a best case; plan for about 1.3-1.7 live.
- **One market:** everything is crypto, so all five depend on the crypto market regime.
- **Weakest component:** the expiry reversal.
- **Status:** an hourly paper-trading forward test (frozen ledger, no look-ahead, minimum 8 weeks) started on 2026-10-15.
