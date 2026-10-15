# Gen67: stress tests and execution improvements (2026-10-15)

**Protocol:** `config/gen67_protocol.json`. **Scripts:** `scripts/gen67_stress.py`, `scripts/gen67_exec.py`, `scripts/gen67_portfolio_prop.py`.

## Execution

| Test | 2022 | 2023–24 | 2025–26 | 2023+ | Verdict |
|---|---|---|---|---|---|
| Cascade, market entry (old) | -0.42 | 1.35 | 0.97 | 1.19 | |
| **Cascade, limit buy -0.25%, 1 hour** | 0.24 | 1.63 | 0.95 | 1.33 | passes |
| **Cascade, limit buy -0.5%, 1 hour** | **0.77** | 1.70 | 0.91 | **1.35** | **adopted** |
| C* weekly rebalance (exits daily) | DEV 1.84 | 1.82 | -0.59 | 0.87 | rejected |
| C* 25% no-trade band | DEV 2.00 | 2.20 | 0.52 | 1.52 (vs 1.55) | rejected |

- **Limit entries:** in a cascade the price usually overshoots a little further after the signal hour, so a limit 0.25–0.5% lower fills on most events (1,479 of 2,002 at -0.5%) at a better price. Unfilled events are skipped.
- **Stop in the fill hour:** if the stop level is also reached in the fill hour, the stop is assumed hit after the fill (conservative).
- **Fill realism:** a touch of the limit counts as filled. The forward test must check real fill rates.

## Portfolio v2

C* + premium carry + cascade with limit entries, equal risk, 15% vol, 2022–26:

| | v1 | **v2** |
|---|---|---|
| Sharpe 2022–26 | 1.56 | **1.83** |
| Sharpe 2023+ | 1.97 | **2.10** |
| Positive months | 61% | **67%** |
| Max drawdown | -17.2% | -20.2% |
| 2022 | -4.7% | **+7.7%** |

Chart: `results/gen67_portfolio.png`.

## Stress test: block bootstrap, 20-day blocks, 2,000 one-year paths (v1)

| | Median year | Bad year (5%) | Very bad year (1%) | P(losing year) | Max DD median / 5% / 1% |
|---|---|---|---|---|---|
| No stop | +21.7% | -3.9% | -11.2% | 9.4% | -8.7% / -16.5% / -21.0% |
| With a -2% daily stop | +17.5% | -8.7% | -18.4% | 15.6% | -10.6% / -20.8% / -25.4% |

The daily stop lowers the portfolio's own return, because it cuts days that recover later. At a prop firm it still pays off, because it prevents daily-loss failures.

## Prop: $100k account, 2 years, challenge 1.0x, funded 0.6x

**Historical** = start every 5 days over 2022–26. **Bootstrap** = 1,000 reshuffled paths.

| Firm | Portfolio, stop | Pass | Historical net | Bootstrap net | Bootstrap unlucky 10% | Bootstrap P(profit) | Months with income |
|---|---|---|---|---|---|---|---|
| HyroTrader 1-Step | v1, none | 74% | $19.8k | $16.9k | $2.1k | 94% | 35% |
| HyroTrader 1-Step | **v2, S50** | 83% | **$26.6k** | **$20.7k** | **$5.6k** | **98%** | **45%** |
| HyroTrader 2-Step | v2, S50 | 92% | $23.4k | $18.4k | $3.1k | 94% | 40% |
| CFT 1-Phase | v2, S50 | 64% | $22.6k | $16.6k | $0.3k | 90% | 42% |
| SizeProp 1-Step | v2, S50 | 69% | $24.3k | $17.7k | $2.6k | 93% | 43% |

**S50 under v2:** it now improves mean and unlucky-10% net at all four firms, so it passes the Gen66 adoption rule.

The bootstrap numbers are the more honest expectation:
- about **$17–21k per $100k account over 2 years**, roughly $700–850 a month on average;
- a payout in about 40–45% of months;
- a 90–98% chance of profit.

A further live haircut of 30–50% is still prudent.
