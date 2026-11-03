# Paper trading v86 - status (2026-10-26 14:10 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-21 15:00 to 2026-10-26 13:00 UTC (119 hours, 6 days)
- Equity: $189,908 (-5.05%), max drawdown -5.64%
- Daily mean -0.853% vs backtest +0.288% (z = -1.81); positive days 17%
- Daily stop hits: 1; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 23.5%
- Gate (config/paper_v86.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* -0.60%, premium carry -2.13%, cascade limit strict +0.00%, trend 4h -1.02%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML -4.16%, alt kimchi -0.10%, premium carry 60 -0.46%