# Paper trading bf26 - status (2026-11-02 08:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-11-02 07:00 UTC (281 hours, 13 days)
- Equity: $193,269 (-3.37%), max drawdown -6.62%
- Daily mean -0.249% vs backtest +0.284% (z = -1.24); positive days 31%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 44.5%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -1.27%, trend 4h -1.74%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium +3.11%, ridge ML -2.34%, vol-managed indices +1.08%, alt kimchi +6.06%, premium carry BF -0.89%