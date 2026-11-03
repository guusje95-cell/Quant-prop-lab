# Paper trading v95 - status (2026-10-26 17:13 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-26 14:00 to 2026-10-26 16:00 UTC (3 hours, 1 days)
- Equity: $199,679 (-0.16%), max drawdown -0.16%
- Daily mean -0.161% vs backtest +0.260% (z = -0.27); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v95.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, cascade limit strict +0.00%, trend 4h -0.14%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML +0.01%, alt kimchi +0.00%, diversifier basket -0.01%, relative crowding 6 +0.01%