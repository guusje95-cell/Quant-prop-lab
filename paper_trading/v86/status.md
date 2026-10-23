# Paper trading v86 - status (2026-10-23 13:23 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-23 12:00 UTC (46 hours, 3 days)
- Equity: $193,589 (-3.21%), max drawdown -3.46%
- Daily mean -1.073% vs backtest +0.288% (z = -1.53); positive days 33%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v86.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.60%, premium carry +0.78%, cascade limit strict +0.00%, trend 4h -0.97%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -4.28%, alt kimchi +0.00%, premium carry 60 +0.19%