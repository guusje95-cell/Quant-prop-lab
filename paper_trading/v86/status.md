# Paper trading v86 - status (2026-10-22 07:10 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-22 06:00 UTC (16 hours, 2 days)
- Equity: $195,421 (-2.29%), max drawdown -2.29%
- Daily mean -1.151% vs backtest +0.288% (z = -1.32); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v86.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.37%, premium carry -0.04%, cascade limit strict +0.00%, trend 4h -0.74%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -2.12%, alt kimchi +0.00%, premium carry 60 -0.04%