# Paper trading v6 (v5 + deleveraging bounce)

v6 runs **next to** v5 with the same rules (HyroTrader 1-Step, risk 1.0, S50 daily stop) and its own folder and ledger.
It adds one sleeve: the Gen89/90 deleveraging bounce. If BTC or ETH open interest (USD value) falls more than 10% in 24h
(to 23:55 UTC) while the price also fell, go long that coin, 0.5 units, for 2 days. Config: `config/paper_v6.json`.

- **Start:** `paper_v6_start.bat` (leave the window open, like v5).
- **Status:** `paper_v6_status.bat`.
- **Share with Claude:** `paper_v6_share.bat`, e.g. weekly together with `paper_v5_share.bat`.
- **Excel:** `paper_trading/v6/paper_v6.xlsx`.
- **No-look-ahead self-test:** passed at 12 cutoffs on 2026-10-19, including 4 moments while the bounce was holding positions.
