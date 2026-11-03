# Paper trading bf26 - status (2026-11-03 17:11 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-11-03 16:00 UTC (314 hours, 14 days)
- Equity: $190,560 (-4.72%), max drawdown -6.62%
- Daily mean -0.332% vs backtest +0.284% (z = -1.49); positive days 29%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 39.8%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -1.83%, trend 4h -1.69%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium +2.34%, ridge ML -1.34%, vol-managed indices -0.27%, alt kimchi +6.53%, premium carry BF -2.15%