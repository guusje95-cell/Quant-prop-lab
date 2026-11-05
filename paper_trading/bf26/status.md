# Paper trading bf26 - status (2026-11-05 20:11 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-11-05 19:00 UTC (365 hours, 16 days)
- Equity: $191,645 (-4.18%), max drawdown -6.62%
- Daily mean -0.252% vs backtest +0.284% (z = -1.39); positive days 31%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 34.2%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -0.52%, trend 4h -2.58%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium -2.17%, ridge ML -3.38%, vol-managed indices +1.18%, alt kimchi +15.20%, premium carry BF -1.46%