# Paper trading "bf": the CFD book for BrightFunded 2-Step Classic swap-free

**Contents and setup**
- **Sleeves (6):** C\* (swap-aware), premium carry (CFD coins), trend 4h, Weiss expiry, deleveraging bounce, Coinbase premium.
- **Costs:** BrightFunded's confirmed conditions. Commission 0.012% per side; measured spreads BTC 0.4 / ETH 2.7 bp; altcoins assumed at 10 bp; swap-free.
- **Leverage:** 1:5 cap on gross exposure.
- **Account:** risk 1.5 (challenge setting), daily stop at 60% of the 5% daily limit.
- **Config:** `config/paper_bf.json`.
- **Backtest:** 2022-26 Sharpe 2.25.

**Use**
- **Start:** `paper_bf_start.bat` (leave it open next to v5 and v6).
- **Status:** `paper_bf_status.bat`.
- **Share:** `paper_bf_share.bat`.
- **Excel:** `paper_trading/bf/paper_bf.xlsx`.

**Checks and limits**
- **Self-test (2026-10-19):** passed at 12 cutoffs with 0 differences; every sleeve was active in at least one window.
- **Prices:** Binance perps stand in for BrightFunded's CFD prices (correlation 0.94-0.96 with Dukascopy CFD prices, Gen77). Real CFD fills will differ slightly.
