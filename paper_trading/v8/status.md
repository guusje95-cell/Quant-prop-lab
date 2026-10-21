# Paper trading v8 - status (2026-10-21 13:09 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-21 08:00 to 2026-10-21 12:00 UTC (5 hours, 1 days)
- Equity: $200,094 (+0.05%), max drawdown 0.00%
- Daily mean +0.047% vs backtest +0.240% (z = -0.13); positive days 100%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v8.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.02%, premium carry +0.29%, cascade limit strict +0.00%, trend 4h -0.00%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -0.26%, alt kimchi +0.00%