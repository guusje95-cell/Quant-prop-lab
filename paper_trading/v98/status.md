# Paper trading v98 - status (2026-11-03 17:11 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-30 16:00 to 2026-11-03 16:00 UTC (97 hours, 5 days)
- Equity: $200,481 (+0.24%), max drawdown -0.49%
- Daily mean +0.049% vs backtest +0.272% (z = -0.31); positive days 20%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate on ALL days (incl. the affected pre-fix period) (config/paper_v98.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, trend 4h -0.27%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -0.10%, alt kimchi +2.01%, diversifier basket -0.53%, relative crowding 6 +0.20%, listing short +0.17%

**Clean validation period (v9.8.1)**: fix active from 2026-11-02 18:26 UTC; clean days from 2026-11-03: **1 of 56**; daily mean -0.491% (z = -0.48), cumulative -0.49%
- Clean gate: **too early**; days before 2026-11-03 are kept and flagged 'affected (pre-fix)'.