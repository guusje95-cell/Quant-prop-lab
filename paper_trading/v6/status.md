# Paper trading v6 - status (2026-10-20 19:07 UTC)

Simulation only. Account $100,000, risk 1.0, firm rules: HyroTrader One-Step $100k.

- Paper period: 2026-10-19 08:00 to 2026-10-20 18:00 UTC (35 hours, 2 days)
- Equity: $100,019 (+0.02%), max drawdown -0.13%
- Daily mean +0.010% vs backtest +0.108% (z = -0.18); positive days 50%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v6.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.01%, premium carry +0.16%, cascade limit strict +0.00%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%