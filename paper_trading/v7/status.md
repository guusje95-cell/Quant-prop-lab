# Paper trading v7 - status (2026-10-21 08:07 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-20 19:00 to 2026-10-21 07:00 UTC (13 hours, 2 days)
- Equity: $199,453 (-0.27%), max drawdown -0.63%
- Daily mean -0.136% vs backtest +0.229% (z = -0.34); positive days 50%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v7.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.03%, premium carry -0.88%, cascade limit strict +0.00%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML +0.22%