# Paper trading bf26 - status (2026-10-30 16:23 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-30 14:00 UTC (216 hours, 10 days)
- Equity: $191,785 (-4.11%), max drawdown -6.62%
- Daily mean -0.408% vs backtest +0.284% (z = -1.42); positive days 30%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 57.9%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -0.85%, trend 4h -1.53%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium +3.97%, ridge ML -1.61%, vol-managed indices -0.21%, alt kimchi +3.91%, premium carry BF -2.16%