# Paper trading v98 - status (2026-11-05 20:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-30 16:00 to 2026-11-05 19:00 UTC (148 hours, 7 days)
- Equity: $205,806 (+2.90%), max drawdown -1.74%
- Daily mean +0.423% vs backtest +0.272% (z = +0.25); positive days 43%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate on ALL days (incl. the affected pre-fix period) (config/paper_v98.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, trend 4h -1.18%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -0.96%, alt kimchi +11.39%, diversifier basket +1.88%, relative crowding 6 +0.07%, listing short +0.12%

**Clean validation period (v9.8.1)**: fix active from 2026-11-02 18:26 UTC; clean days from 2026-11-03: **3 of 56**; daily mean +0.740% (z = +0.51), cumulative +2.15%
- Clean gate: **too early**; days before 2026-11-03 are kept and flagged 'affected (pre-fix)'.