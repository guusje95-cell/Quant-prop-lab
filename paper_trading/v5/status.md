# Paper trading v5 - status (2026-10-19 16:07 UTC)

Simulation only. Account $100,000, risk 1.0, firm rules: HyroTrader One-Step $100k.

- Paper period: 2026-10-15 15:00 to 2026-10-19 15:00 UTC (97 hours, 5 days)
- Equity: $99,858 (-0.14%), max drawdown -0.46%
- Daily mean -0.028% vs backtest +0.104% (z = -0.38); positive days 60%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v5.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.21%, premium carry +0.98%, cascade limit strict +0.00%, trend 4h -0.40%, Weiss expiry +0.00%