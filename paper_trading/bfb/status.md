# Paper trading bfb - status (2026-10-20 18:07 UTC)

Simulation only. Account $100,000, risk 1.5, firm rules: BrightFunded Two-Step Classic $100k.

- Paper period: 2026-10-20 08:00 to 2026-10-20 17:00 UTC (10 hours, 1 days)
- Equity: $98,744 (-1.26%), max drawdown -1.26%
- Daily mean -1.256% vs backtest +0.162% (z = -1.22); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bfb.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.05%, premium carry -2.29%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium -2.04%