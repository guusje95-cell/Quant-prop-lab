# Gen69: robustness of v3, near-misses inside the portfolio, prop sizing (2026-10-15)

**Protocol:** `config/gen69_protocol.json`. **Scripts:** `scripts/gen69_v3_robust.py`, `scripts/gen69_prop_sizing.py`.

## M1: near-misses inside the portfolio (2022–26, ~15% vol)

| Portfolio | Sharpe | Max DD | Positive months | Bootstrap 5%-worst year | P(losing year) | 2022 |
|---|---|---|---|---|---|---|
| No vol targeting (core 3 sleeves) | 1.77 | -20.1% | 61% | -0.4% | 5.2% | +5.6% |
| v3 (core + vol targeting) | 1.88 | -13.3% | 63% | +1.8% | 4.0% | +3.6% |
| **v3 + 4h trend = v4** | **1.95** | **-12.1%** | **68%** | +1.8% | 3.8% | +8.3% |
| v3 + Friday-expiry window | 2.09 | -10.7% | 72% | +4.6% | 2.6% | +7.9% |
| v3 + both | 2.15 | -11.4% | 68% | +5.4% | 2.2% | +9.9% |

**Expiry window: forward test only, small size.**
- It fires 12 times a year (fewer than 100 events in total).
- Equal-risk scaling would put 2.6x leverage on it.
- Its worst single event is -7.7% at unit notional.
- Its tail cannot be estimated from so few events.

**4h trend: added.** It is dense, passes the M1 rule, and earns in 2022.

## M3: vol-targeting robustness (Sharpe / max DD)

| Lookback | Cap 1.25 | Cap 1.5 | Cap 2.0 |
|---|---|---|---|
| 14d | 1.77 / -17.0% | 1.75 / -16.2% | 1.78 / -14.4% |
| 30d | 1.85 / -14.4% | **1.88 / -13.3%** | 1.97 / -12.1% |
| 60d | 1.89 / -13.2% | 1.89 / -12.1% | 1.96 / -11.3% |

No vol targeting: 1.77 / -20.1%.

- **Drawdown benefit:** robust, with max DD better at every setting.
- **Sharpe benefit:** not robust. The 14-day versions do not beat 1.77 (14d / cap 1.5 gives 1.75).
- **Strictly, the pre-registered rule fails on that one neighbour.** Vol targeting is kept as a drawdown control, and its Sharpe gain is not counted as proven.

## M4: cascade neighbours (strict limit fills)

Max open 3 / hold 12 gives 1.88. The neighbours (K, H) = (5,12), (3,24), (5,24) give 1.78, 1.81, 1.84, all with max DD around -13%. So it is robust.

## Bug caught

The first hourly version of the 4h trend applied each 4-hour position from the first hour of its bar instead of after the bar closed (look-ahead). That produced an impossible Sharpe of 3.9, which is how it was caught. After the fix, the hourly sleeve matches the daily one exactly (correlation 1.00; DEV 0.77, TEST 1.43, HOLD 0.44). The other hourly sleeves were checked and are clean.

## M7: prop sizing for v4

S50 daily stop, bootstrap 500 paths, $100k, 2 years. Descriptive: chosen on the same data.

| Firm | Challenge / funded | Pass | Bootstrap net | Unlucky 10% | P(profit) | Payout months |
|---|---|---|---|---|---|---|
| HyroTrader 1-Step | 1.0 / 0.6 (moderate) | 82% | $22.5k | $7.5k | 98% | 44% |
| HyroTrader 1-Step | 1.25 / 0.8 (grid edge) | 79% | $31.4k | $10.7k | 99% | 49% |
| HyroTrader 2-Step | 1.0 / 0.6 | 91% | $20.2k | $5.8k | 97% | 48% |
| HyroTrader 2-Step | 1.25 / 0.8 | 82% | $28.8k | $9.1k | 98% | 49% |
| SizeProp 1-Step | 1.0 / 0.6 | 78% | $21.0k | $5.6k | 97% | 51% |
| CFT 1-Phase | 0.75 / 0.4 | 80% | $12.4k | $3.2k | 96% | 49% |

- **Higher funded risk raises the average** at HyroTrader, but 1.25 / 0.8 sits on the edge of the grid. 1.0 / 0.6 is the safer recommendation.
- **CFT (6% trailing max loss)** does best at low risk.
