# Paper trading v96 - status (2026-10-27 18:09 UTC)

Simulation only. Account $200,000, risk 2.0, firm rules: HyroTrader Two-Step $200k.

- Paper period: 2026-10-26 17:00 to 2026-10-27 17:00 UTC (25 hours, 2 days)
- Equity: $199,548 (-0.23%), max drawdown -0.34%
- Daily mean -0.113% vs backtest +0.271% (z = -0.35); positive days 50%
- Daily stop hits: 0; firm daily-limit breaches: 0; max-loss breaches: 0
- Weiss expiry events: 0; late hours: 0.0%
- Gate (config/paper_v96.json): **too early**

Sleeve P&L so far (sum of hourly returns, unit size): C* +0.00%, cascade limit strict +0.00%, trend 4h -0.07%, Weiss expiry +0.00%, delev bounce +0.00%, ridge ML +0.41%, alt kimchi -0.04%, diversifier basket -0.16%, relative crowding 6 +0.05%, listing short -0.70%