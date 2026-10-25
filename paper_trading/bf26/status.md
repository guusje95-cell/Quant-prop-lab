# Paper trading bf26 - status (2026-10-24 05:09 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-24 03:00 UTC (61 hours, 4 days)
- Equity: $192,011 (-3.99%), max drawdown -3.99%
- Daily mean -1.009% vs backtest +0.284% (z = -1.67); positive days 0%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -0.57%, trend 4h -1.06%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium +1.07%, ridge ML -2.04%, vol-managed indices -1.05%, alt kimchi +0.00%, premium carry BF -1.92%