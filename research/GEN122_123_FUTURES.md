# Gen122-123 (2026-10-20): futures rounds 2 and 3 (8 trials)

All tests were pre-registered (config/gen122_protocol.json, config/gen123_protocol.json) and run on Databento CME hourly data, net of 1 tick + commission per side (micro contracts where they exist). Splits: DEV 2010-17, TEST 2018-22, HOLD 2023-26/09. Rule: DEV > 0, TEST >= 0.5, HOLD >= 0.3.

| Test | DEV | TEST | HOLD | corr v6 | Prop fit | Verdict |
|---|---|---|---|---|---|---|
| F1 overnight drift at the European open (02-04 ET) | -2.02 | -0.40 | -0.01 | 0.01 | in-session | rejected |
| F2 F1 after a down day | -1.02 | 0.02 | 0.27 | -0.05 | in-session | rejected |
| F3 month-end Treasury demand (ZN/ZB/ZF) | 0.98 | 0.94 | 0.05 | -0.02 | multi-day | rejected: worked 2010-22, gone since 2023 |
| F4 FX carry cross-section | 0.11 | -0.73 | -0.03 | 0.02 | multi-day | rejected |
| **F5 vol-managed long ES/NQ** | **1.05** | **0.55** | **0.98** | 0.09 | multi-day | **passes the rule, but it is equity beta** |
| G1 TSMOM 12m, 24 markets | 0.26 | 0.42 | 0.39 | -0.03 | multi-day | rejected (TEST just short) |
| G2 F5 in-session only (flat 16-18 ET) | 0.24 | 0.22 | 0.63 | 0.09 | in-session | rejected: a daily round trip eats the edge |
| G3 risk parity ES/ZN/GC | 0.95 | 0.26 | 0.89 | 0.06 | multi-day | rejected (2022) |

## F5: what it really is
- **Same Sharpe as buy-and-hold:** buy-and-hold of ES/NQ at the same average exposure (0.56) scores 1.07 / 0.47 / 1.17, against F5's 1.05 / 0.55 / 0.98.
- **What vol management buys:** a smaller drawdown (max DD -22% vs -35% at about 16% vol) and a smoother 2022 (-20% vs -30%). It adds little Sharpe.
- **Return profile:** 14% a year at 16% vol. Years: 2018 -0.2%, 2022 -19.9%, 2023 +27%, 2024 +16.5%, 2025 +8.6%.
- **Usefulness:** it is a diversifier (correlation 0.09 with v6). It is not an edge. It fits only firms that allow overnight holding (MFFU Core/Rapid/Flex/Pro, Tradeify; unverified). At prop drawdown limits (about 4-6% trailing) it would have to run at about 5% vol, which gives about 4-5% a year.

## Bottom line for futures (20 trials across Gen114/115/122/123)
- **Prop-compatible intraday or in-session strategies** (Topstep, Lucid): none passes on hourly data.
- **Multi-day:** only equity beta with vol management passes, and that is not a real edge.
- **Most solid near-miss:** 12-month time-series momentum (TEST 0.42).
- **What could still change this:** finer data (1-minute) for intraday setups, or a different market structure (e.g. option-implied signals). Plain hourly price patterns in liquid futures are close to efficient after costs.
