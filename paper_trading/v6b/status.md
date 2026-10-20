# Paper trading v6b - status (2026-10-20 18:08 UTC)

Simulation only. Account $100,000, risk 1.0, firm rules: HyroTrader One-Step $100k.

- Paper period: 2026-10-20 08:00 to 2026-10-20 17:00 UTC (10 hours, 1 days)
- Equity: $99,426 (-0.57%), max drawdown -0.57%
- Daily mean -0.574% vs backtest +0.111% (z = -0.90); positive days 0%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v6b.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.05%, premium carry -1.95%, cascade limit strict +0.00%, trend 4h +0.00%, Weiss expiry +0.00%, delev bounce +0.00%