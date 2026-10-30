# Paper trading v98 - status (2026-10-30 18:11 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-30 16:00 to 2026-10-30 17:00 UTC (2 hours, 1 days)
- Equity: $199,588 (-0.21%), max drawdown -0.21%
- Daily mean -0.206% vs backtest +0.272% (z = -0.30); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v98.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, trend 4h +0.01%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -0.11%, alt kimchi -0.78%, diversifier basket +0.05%, relative crowding 6 -0.03%, listing short +0.05%