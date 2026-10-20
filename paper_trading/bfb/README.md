# Shadow paper test bf-b (config/paper_bfb.json)

bf-b is the BrightFunded CFD book with ONE change: premium carry trades all 42 BrightFunded-listed coins instead of 11 (Gen121).
Every other sleeve is unchanged. It runs next to bf, which stays the main CFD book until this test decides.

- **Start:** double-click `paper_bfb_start.bat` and leave the window open. It also downloads the extra coins (public Binance data, no key).
- **Share weekly:** `paper_bfb_share.bat`.
- **Decision after >= 56 days:** bf-b replaces bf only if, over the same hours, its paper result is not worse than bf's and its reconciliation is OK.
- **Backtest 2022-26:** 2.41 (bf: 2.25); book TEST 2023-24 3.18 vs 3.45.
- **Spread caveat:** the new coins assume a 10 bp spread (not yet checked in MT5). Check a few of them (SNX, INJ, HBAR, SUI, OP) in MT5 during market hours.
