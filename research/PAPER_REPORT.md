# Paper report (2026-10-23 19:36 UTC)

Simulation only. Rules: config/paper_monitor.json and the gates in config/paper_v86.json / paper_bf26.json. The paper code is never changed because of these numbers.

## Alerts

- bf26: reconcile not clean (45 hours, correlation 0.9366, cumulative difference +0.628% of the account -> **INVESTIGATE**)

## v86 (2026-10-21 15:00 to 2026-10-23 12:00 UTC, 46 h, 3 days)

- Equity $193,589 (-3.21%) at risk 2.0; max drawdown -3.46%
- Daily mean -1.073% vs backtest +0.288%: z = -1.53 (one standard error of the mean is 0.89% a day at 3 days)
- Daily stops: 1 (max 1 in 14 days); firm breaches: 0 daily / 0 max
- Weiss expiries: 0; late hours 0.0%; reconcile: 46 hours, correlation 1.0000, cumulative difference +0.000% of the account -> **OK**
- Gate: **too early**

| Sleeve | Cumulative unit P&L | Alert level (-3 sd x sqrt(days)) |
|---|---|---|
| C* | -0.60% | -3.14% |
| premium carry | +0.78% | -5.66% |
| cascade limit strict | +0.00% | -3.46% |
| trend 4h | -0.97% | -1.71% |
| Weiss expiry | +0.00% | -0.53% |
| delev bounce | +0.00% | -2.55% |
| ridge ML | -4.28% | -7.67% |
| alt kimchi | +0.00% | -13.85% |
| premium carry 60 | +0.19% | -4.22% |

## bf26 (2026-10-21 15:00 to 2026-10-23 11:00 UTC, 45 h, 3 days)

- Equity $195,610 (-2.20%) at risk 2.0; max drawdown -3.32%
- Daily mean -0.725% vs backtest +0.284%: z = -1.13 (one standard error of the mean is 0.89% a day at 3 days)
- Daily stops: 1 (max 1 in 14 days); firm breaches: 0 daily / 0 max
- Weiss expiries: 0; late hours 0.0%; reconcile: 45 hours, correlation 0.9366, cumulative difference +0.628% of the account -> **INVESTIGATE**
- Gate: **too early**

| Sleeve | Cumulative unit P&L | Alert level (-3 sd x sqrt(days)) |
|---|---|---|
| C* | -0.55% | -2.72% |
| premium carry | +1.82% | -6.75% |
| trend 4h | -0.95% | -1.69% |
| Weiss expiry | +0.00% | -0.54% |
| delev bounce | +0.00% | -2.53% |
| coinbase premium | +0.21% | -7.13% |
| ridge ML | -2.54% | -7.11% |
| vol-managed indices | -0.90% | -5.59% |
| alt kimchi | +0.00% | -12.55% |
| premium carry BF | -0.36% | -4.71% |

## Per-firm accounts (v86 ledger)

| Firm | Risk / stop | Equity | Return | Distance to max-loss floor | Stops | Daily / max breaches | Target 1 |
|---|---|---|---|---|---|---|---|
| Hyro 2-Step 200k | 2.0 / 2.5% | $193,589 | -3.21% | 6.79% of the account | 1 | 0 / 0 | 10% not yet |
| CFT 2-Phase 200k | 2.0 / 2.5% | $193,589 | -3.21% | 6.79% of the account | 1 | 0 / 0 | 8% not yet |
| Propr 2-Step 100k | 1.0 / 3.0% | $98,441 | -1.56% | 6.43% of the account | 0 | 0 / 0 | 5% not yet |
| MFP Signature 100k | 1.0 / 1.2% | $98,338 | -1.66% | 4.34% of the account | 1 | 0 / 0 | 10% not yet |

