# Paper trading v5 - status (2026-10-18 14:07 UTC)

Simulation only. Account $100,000, risk 1.0, firm rules: HyroTrader One-Step $100k.

- Paper period: 2026-10-15 15:00 to 2026-10-18 13:00 UTC (71 hours, 4 days)
- Equity: $99,841 (-0.16%), max drawdown -0.46%
- Daily mean -0.040% vs backtest +0.104% (z = -0.37); positive days 75%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v5.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.27%, premium carry +0.22%, cascade limit strict +0.00%, trend 4h -0.11%, Weiss expiry +0.00%