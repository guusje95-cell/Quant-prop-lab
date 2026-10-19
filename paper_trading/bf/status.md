# Paper trading bf - status (2026-10-19 16:07 UTC)

Simulation only. Account $100,000, risk 1.5, firm rules: BrightFunded Two-Step Classic $100k.

- Paper period: 2026-10-19 10:00 to 2026-10-19 15:00 UTC (6 hours, 1 days)
- Equity: $100,180 (+0.18%), max drawdown 0.00%
- Daily mean +0.180% vs backtest +0.156% (z = +0.02); positive days 100%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bf.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.03%, premium carry -0.24%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium +1.38%