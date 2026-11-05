# Paper trading v98 - status (2026-11-05 16:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-30 16:00 to 2026-11-05 15:00 UTC (144 hours, 7 days)
- Equity: $207,214 (+3.61%), max drawdown -1.74%
- Daily mean +0.524% vs backtest +0.272% (z = +0.42); positive days 43%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate on ALL days (incl. the affected pre-fix period) (config/paper_v98.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, trend 4h -1.23%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -0.71%, alt kimchi +13.60%, diversifier basket +2.05%, relative crowding 6 +0.04%, listing short +0.11%

**Clean validation period (v9.8.1)**: fix active from 2026-11-02 18:26 UTC; clean days from 2026-11-03: **3 of 56**; daily mean +0.977% (z = +0.77), cumulative +2.85%
- Clean gate: **too early**; days before 2026-11-03 are kept and flagged 'affected (pre-fix)'.