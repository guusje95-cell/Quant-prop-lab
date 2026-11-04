# Paper trading v98 - status (2026-11-04 17:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-30 16:00 to 2026-11-04 16:00 UTC (121 hours, 6 days)
- Equity: $198,472 (-0.76%), max drawdown -1.54%
- Daily mean -0.125% vs backtest +0.272% (z = -0.61); positive days 33%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate on ALL days (incl. the affected pre-fix period) (config/paper_v98.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, trend 4h -0.15%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -5.07%, alt kimchi +5.03%, diversifier basket -0.56%, relative crowding 6 +0.26%, listing short -0.02%

**Clean validation period (v9.8.1)**: fix active from 2026-11-02 18:26 UTC; clean days from 2026-11-03: **2 of 56**; daily mean -0.743% (z = -0.91), cumulative -1.49%
- Clean gate: **too early**; days before 2026-11-03 are kept and flagged 'affected (pre-fix)'.