# Paper trading bf26 - status (2026-11-05 16:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: BrightFunded Two-Step Classic $200k.

- Paper period: 2026-10-21 15:00 to 2026-11-05 14:00 UTC (360 hours, 16 days)
- Equity: $187,772 (-6.11%), max drawdown -6.62%
- Daily mean -0.381% vs backtest +0.284% (z = -1.72); positive days 31%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 1; late hours: 34.7%
- Gate (config/paper_bf26.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.55%, premium carry -1.32%, trend 4h -2.10%, Weiss expiry -0.53%, delev bounce +0.00%, coinbase premium -2.17%, ridge ML -4.98%, vol-managed indices +0.98%, alt kimchi +11.98%, premium carry BF -2.66%