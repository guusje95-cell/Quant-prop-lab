# Paper trading bf26 - status (2026-10-22 07:10 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-22 05:00 UTC (15 hours, 2 days)
- Equity: $196,057 (-1.97%), max drawdown -1.97%
- Daily mean -0.990% vs backtest +0.284% (z = -1.17); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.30%, premium carry -0.18%, trend 4h -0.66%, Weiss expiry +0.00%, delev bounce +0.00%, coinbase premium +0.72%, ridge ML -0.80%, vol-managed indices -0.44%, alt kimchi +0.00%, premium carry BF -0.56%