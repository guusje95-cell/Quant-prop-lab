# Shadow paper test v6b (config/paper_v6b.json)

v6b is v6 with ONE change: premium carry trades 60 Binance coins instead of 20 (Gen80 breadth, research/GEN114_121_NEW_DATA.md).
It runs next to v6. v6 stays the main book until this test decides.

- **Start:** double-click `paper_v6b_start.bat` and leave the window open, just like v6. It also downloads the 40 extra coins (public Binance data, no key).
- **Share weekly:** `paper_v6b_share.bat`.
- **Decision after >= 56 days:** v6b replaces v6 only if, over the same hours, its paper result is not worse than v6's and its reconciliation is OK. Otherwise it is dropped.
- **Backtest 2022-26:** Sharpe 2.54 (v6: 2.46). Book TEST 2023-24 is lower (3.14 vs 3.44), which is why this is a shadow test and not an adoption.
