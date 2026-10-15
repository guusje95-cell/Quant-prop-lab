# Gen72: optimisation of the crypto sleeves and the final crypto portfolio (v5)

- **Protocol:** `config/gen72_protocol.json`, registered before any number was computed.
- **Scripts:** `scripts/gen72_optimise.py` (sleeve grids) and `scripts/gen72_portfolio_report.py` (portfolio, report, prop).
- **Chart:** `results/gen72_report.png`.
- **Tables:** `results/gen72_grid.csv`, `gen72_choice.csv`, `gen72_portfolio.csv`, `gen72_stats.csv`, `gen72_monthly.csv`, `gen72_prop.csv`.

## 1. Sleeve tuning: 104 grid cells, plateau rule, walk-forward check

| Sleeve | Default | Best on DEV (plateau-smoothed) | 2023-26 default | 2023-26 tuned | Walk-forward 2023-26 | v4 with tuned | Verdict |
|---|---|---|---|---|---|---|---|
| premium carry | 7d / hold 7d / terciles | 21d / 7d / quartiles | 0.87 | 0.69 | 0.42 | 1.94 | keep default |
| trend 4h | 20/10, BTC/ETH/SOL | 40/20, 6 coins | 0.93 | 0.87 | 0.70 | 1.89 | keep default |
| cascade (strict limit) | k=3, 12h, -0.5%, OI -5% | k=2.5, 12h, -0.8%, OI -5% | 1.30 | 0.91 | 1.10 | 1.90 | keep default |

**Result: tuning makes every sleeve worse out of sample.** Parameters picked on the past, even with plateau smoothing, lose to the current settings in 2023-26. Re-optimising every year (walk-forward) loses as well. So the sleeves are not under-optimised: their edge sits in the rule, not in the exact numbers. More tuning would only fit noise. All defaults stay; C* (an ensemble of 19 lookbacks) was left frozen as registered.

## 2. Portfolio construction (point-in-time)

| Method | 2022-24 | HOLD 2025-26 | 2022-26 | Max DD |
|---|---|---|---|---|
| P0 v4 recipe (full-sample vols, look-ahead in the scale; reference) | 2.67 | 1.64 | 2.29 | -9.6% |
| **P1 point-in-time equal risk (chosen)** | 2.58 | **1.66** | **2.25** | **-9.5%** |
| P2 equal risk contribution | 2.60 | 1.60 | 2.25 | -9.3% |
| P3 minimum variance (shrunk) | 2.11 | 1.79 | 2.00 | -10.3% |

- **Rule:** P2 is best on 2022-24 but loses to P1 in HOLD, so P1 is used, as registered.
- **Honesty fix:** P1 removes the small look-ahead in the old recipe; each sleeve's scale now uses only its trailing 365 days.
- **Recompute schedule:** weights are recomputed at each month start.
- **Weiss expiry:** held at half its equal-risk weight (Gen70). That gives about 1.1x equity notional for 2 hours once a month; its worst 2022-26 event cost the portfolio 1.4%.

**A bug caught and fixed:** the first run dropped the Weiss sleeve. A "live sleeve" filter needed 30 non-zero days a year, and Weiss trades only 12. The filter was changed to 6 events for Weiss before any result was used.

## 3. Final crypto portfolio v5: C* + premium carry + cascade (strict limit) + 4h trend + Weiss expiry (half weight)

All figures are 2022-01 to 2026-09 at 15% annual vol, net of fees, slippage and funding.

| | **v5 (final)** | v4 (previous) | C* | premium carry | trend 4h | cascade | Weiss expiry |
|---|---|---|---|---|---|---|---|
| Sharpe | **2.25** | 1.94 | 1.28 | 0.71 | 0.85 | 1.20 | 1.11 |
| Sortino | **4.33** | 3.52 | 2.03 | 1.04 | 1.45 | 2.52 | 2.25 |
| CAGR | **38.7%** | 32.3% | 19.9% | 10.0% | 12.3% | 18.4% | 16.9% |
| Max DD | **-9.5%** | -12.0% | -15.7% | -16.9% | -15.0% | -16.6% | -15.9% |
| Calmar | **4.08** | 2.69 | 1.27 | 0.59 | 0.82 | 1.11 | 1.06 |
| Longest DD (days) | 172 | 157 | 435 | 399 | 381 | 341 | 455 |
| Positive months | **72%** | 68% | 42% | 65% | 53% | 53% | 68% |
| Worst month | -4.2% | -4.9% | -4.2% | -9.3% | -7.0% | -6.7% | -11.2% |
| Worst day | -3.6% | -3.7% | -6.0% | -4.2% | -5.1% | -5.6% | -11.2% |
| 2022 (bear market) | +18.8% | +7.7% | -6.1% | +1.6% | +8.0% | +14.0% | +11.7% |
| 2023 | +63.3% | +52.4% | +45.3% | +10.5% | +23.4% | +15.2% | +17.8% |
| 2024 | +64.0% | +55.4% | +53.7% | +9.3% | +17.8% | +42.6% | +36.3% |
| 2025 | +10.6% | +14.5% | +2.3% | +16.1% | -6.3% | +4.7% | +7.8% |
| 2026 (Jan-Sep) | +34.2% | +29.5% | +10.4% | +10.6% | +17.7% | +14.0% | +8.5% |

**Correlations (daily, 2022-26).** The largest pair is C* / trend 4h at 0.33. Every other pair lies between -0.07 and +0.19, and Weiss is about 0 with everything.

**Monthly returns, v5 (%)**

| | J | F | M | A | M | J | J | A | S | O | N | D | Year |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 3.3 | -3.0 | 3.6 | -0.0 | 2.2 | 11.4 | 1.4 | 0.2 | -3.3 | 5.0 | -0.6 | -1.9 | **18.8** |
| 2023 | 17.3 | -0.8 | 0.9 | 1.2 | -0.1 | 11.8 | 0.1 | 4.8 | 0.6 | 11.7 | 3.1 | 1.4 | **63.3** |
| 2024 | 3.7 | 12.9 | 3.6 | 1.4 | 0.7 | 1.3 | 5.7 | -3.1 | 0.2 | 4.2 | 21.8 | 0.3 | **64.0** |
| 2025 | 0.4 | -0.1 | -4.2 | 1.9 | 1.8 | -3.0 | 4.8 | 0.7 | -0.7 | 2.7 | 10.2 | -3.6 | **10.6** |
| 2026 | 9.3 | -0.1 | 0.8 | -0.5 | 4.3 | 3.4 | -2.9 | 13.5 | 3.1 | | | | **34.2** |

## 4. Prop firms: v5, $100k account, 2 years

Settings: bootstrap (500 paths, 20-day blocks), daily stop at 50% of the firm's daily limit, 5 attempts.

| Firm | Risk (challenge / funded) | Pass | Days to pass | Mean net | Unlucky 10% | P(profit) | Months with payout |
|---|---|---|---|---|---|---|---|
| HyroTrader 1-Step | 0.75 / 0.4 | 98% | 126 | $17.0k | $7.7k | 99% | 54% |
| **HyroTrader 1-Step** | **1.0 / 0.6** | 87% | 95 | **$26.4k** | **$12.0k** | **99.6%** | 58% |
| HyroTrader 1-Step | 1.25 / 0.8 | 78% | 63 | $34.8k | $14.1k | 99% | 55% |
| HyroTrader 2-Step | 1.0 / 0.6 | 99.8% | 156 | $23.9k | $9.9k | 98% | 54% |
| HyroTrader 2-Step | 1.25 / 0.8 | 90% | 123 | $33.3k | $12.6k | 99% | 56% |
| SizeProp 1-Step | 1.0 / 0.6 | 78% | 85 | $24.2k | $9.0k | 98% | 60% |
| CFT 1-Phase | 0.75 / 0.4 | 75% | 108 | $13.4k | $4.4k | 98% | 60% |
| CFT 1-Phase | 1.0 / 0.6 | 65% | 74 | $21.8k | $5.9k | 97% | 58% |

Compared with v4 at HyroTrader 1-Step 1.0 / 0.6: mean $22.5k → $26.4k, unlucky 10% $7.5k → $12.0k.

## 5. How much to trust this
- **Selection bias.** The sleeves were chosen after seeing 2022-26, so this Sharpe is an in-sample best case. Each sleeve passed a held-out period, but the portfolio as a whole has no untouched data left. For planning, assume a live Sharpe of about **1.3-1.7**, not 2.25.
- **2025 shows a bad year.** Sharpe ~0.7, +10.6% with several small losing months. That is what a weak crypto year looks like for this mix.
- **Weiss expiry is the least proven part.** It has 81 events and t = 1.6. Remove it and the portfolio is v4 with point-in-time scaling (Sharpe ~2.0).
- **Next step:** paper-trade the full v5 next to the backtest before any challenge is bought.
