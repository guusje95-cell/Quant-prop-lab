# Gen68: fill realism, maker rebalancing, drawdown attribution and controls (2026-10-15)

**Protocol:** `config/gen68_protocol.json`. **Scripts:** `scripts/gen68_exec_dd.py`, `scripts/gen68_portfolio_prop.py`.

## L1: are the cascade limit fills real?

A fill is counted only if Binance 5-minute data shows the next hour's low at or below the limit. The question is how strict that rule needs to be (queue position is unknown).

| Fill rule (limit -0.5%) | 2022 | 2023–24 | 2025–26 | 2023+ | Active days |
|---|---|---|---|---|---|
| Touch | 1.05 | 1.86 | 0.87 | 1.41 | 502 |
| **0.1% trade-through** | 0.87 | 1.73 | 0.79 | **1.30** | 465 |
| 0.3% trade-through | 0.70 | 1.04 | 0.00 | 0.57 | 416 |
| Market entry (v1) | -0.26 | 1.42 | 0.93 | 1.20 | 632 |

- The gain survives a realistic 0.1% trade-through, but not 0.3%. So the forward test must measure real fill quality.
- From now on, the portfolio uses the 0.1% trade-through version.

## L2: maker rebalancing for C* and premium carry: rejected

| | DEV | 2023+ |
|---|---|---|
| C* taker | 2.00 | 1.55 |
| C* maker at 00:00, else 01:00 | 1.97 | 1.54 |
| Premium carry taker | 0.90 | 0.96 |
| Premium carry maker | 0.87 | 0.89 |

About 92–94% of orders fill, but the cost saving is lost to adverse selection.

## D1: where the drawdowns come from (v2)

| Peak to trough | Drawdown | C* | Premium carry | Cascade |
|---|---|---|---|---|
| 2024-12-03 to 2025-03-08 | -20.2% | -4.6 | -6.0 | -6.9 |
| 2022-01-19 to 2022-05-09 | -9.0% | -1.0 | -2.6 | -5.2 |
| 2024-07-29 to 2024-08-19 | -6.7% | -1.2 | -2.6 | -2.3 |

The deepest drawdown (winter 2024–25) hit all three sleeves at once.

## D2: drawdown controls (v2, 2022–26)

| | Sharpe | Max DD | Bootstrap 5%-worst year | P(losing year) |
|---|---|---|---|---|
| Baseline (equal risk) | 1.83 | -20.2% | +0.4% | 4.7% |
| **Portfolio vol targeting, 30d, cap 1.5x** | **1.96** | **-13.5%** | **+3.0%** | **3.2%** |
| Sleeve drawdown brake | 1.75 | -20.8% | -1.0% | 5.6% |

**Portfolio vol targeting is adopted.** The sleeve brake is rejected.

## Portfolio v3

C* + premium carry + cascade (limit -0.5%, 0.1% trade-through) at equal risk, plus portfolio vol targeting, at 15% vol, 2022–26.

| | Sharpe | CAGR | Max DD | Positive months | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---|---|---|---|---|---|---|---|---|---|
| **v3** | **1.88** | 31% | **-13.3%** | 63% | +4% | +47% | +53% | +23% | +26% |
| v2 | 1.83 | 30% | -20.2% | 67% | +8% | +46% | +61% | +15% | +20% |
| v1 | 1.56 | 25% | -17.2% | 61% | -5% | +41% | +56% | +17% | +19% |
| C* alone | 1.28 | 20% | -15.7% | 42% | -6% | +45% | +54% | +2% | +10% |

Chart: `results/gen68_portfolio.png`.

## Prop with v3

S50 daily stop, challenge 1.0x / funded 0.6x, $100k, 2 years. Bootstrap = 1,000 reshuffled paths.

| Firm | Pass | Daily fails | Historical net | **Bootstrap net** | Bootstrap unlucky 10% | Bootstrap P(profit) | Months with income |
|---|---|---|---|---|---|---|---|
| HyroTrader 1-Step | 77% | 0% | $24.4k | **$20.3k** | $6.8k | **98.5%** | **52%** |
| HyroTrader 2-Step | 86% | 0% | $21.0k | $17.5k | $4.1k | 95.5% | 46% |
| SizeProp 1-Step | 74% | 0% | $23.3k | $17.9k | $3.5k | 95.1% | **57%** |
| CFT 1-Phase | 57% | 0% | $17.8k | $15.3k | $0.2k | 90.1% | 40% |
