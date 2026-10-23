# Paper trading bf26 - status (2026-10-23 13:20 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-23 11:00 UTC (45 hours, 3 days)
- Equity: $195,610 (-2.20%), max drawdown -3.32%
- Daily mean -0.725% vs backtest +0.284% (z = -1.13); positive days 33%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry +1.82%, trend 4h -0.95%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium +0.21%, ridge ML -2.54%, vol-managed indices -0.90%, alt kimchi +0.00%, premium carry BF -0.36%