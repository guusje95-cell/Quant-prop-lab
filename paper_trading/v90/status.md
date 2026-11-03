# Paper trading v90 - status (2026-10-26 17:12 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-25 18:00 to 2026-10-26 16:00 UTC (23 hours, 2 days)
- Equity: $201,202 (+0.60%), max drawdown -0.08%
- Daily mean +0.301% vs backtest +0.225% (z = +0.07); positive days 50%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v90.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, cascade limit strict +0.00%, trend 4h +0.24%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML +0.60%, alt kimchi -0.07%