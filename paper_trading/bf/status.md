# Paper trading bf - status (2026-10-20 19:07 UTC)

Simulation only. Account $100,000, risk 1.5, firm rules: BrightFunded Two-Step Classic $100k.

- Paper period: 2026-10-19 10:00 to 2026-10-20 18:00 UTC (33 hours, 2 days)
- Equity: $99,691 (-0.31%), max drawdown -0.44%
- Daily mean -0.154% vs backtest +0.156% (z = -0.38); positive days 50%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bf.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.01%, premium carry -1.06%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium +0.07%