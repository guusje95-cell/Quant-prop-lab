# Paper trading bf26 - status (2026-11-04 17:11 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-11-04 15:00 UTC (337 hours, 15 days)
- Equity: $188,055 (-5.97%), max drawdown -6.62%
- Daily mean -0.397% vs backtest +0.284% (z = -1.71); positive days 27%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 37.1%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -1.42%, trend 4h -1.62%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium -2.06%, ridge ML -6.41%, vol-managed indices +1.24%, alt kimchi +8.61%, premium carry BF -1.48%