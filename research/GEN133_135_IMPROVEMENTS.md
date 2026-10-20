# Gen133-135 + P6 (2026-10-20): what improved

## 1. Futures book (Gen135): honest out-of-sample pass
- **Protocol:** `config/gen135_protocol.json`. The pool is every daily futures sleeve tested since Gen114 (2010+ data).
- **Selection rule:** Sharpe 2010-17 > 0 AND 2018-22 > 0.3. **No 2023+ data was used.**
- **Selected (5):**
  - F3 month-end Treasury demand
  - F5 vol-managed long ES/NQ
  - G1 12-month TSMOM (24 markets)
  - P1 IBS reversal (index futures)
  - A3 Treasury auction round trip
- **Book construction:** point-in-time equal risk (inverse 365-day vol, monthly), 10% vol target (60-day, cap 3x).

| | 2010-17 | 2018-22 | **2023-26 (out of sample)** |
|---|---|---|---|
| Futures book | 0.98 | 0.81 | **0.59** (bar 0.5) -> **PASS** |

- **2023-26 profile:** about 6.4% a year at 10% vol, max DD -9.9%.
- **Correlation 2023-26:** v6 0.04, bf -0.01.
- **Prop fit:** multi-day holdings (overnight), so MFFU (semi-automated) / Tradeify; not Topstep/Lucid.
- **Honest caveats:**
  - 0.59 is modest, and the in-sample columns are selection-inflated.
  - F5 is equity beta.
  - P1 entered with a DEV Sharpe of 0.004 (just above 0).
  - Each sleeve alone was a near-miss. The book works through diversification.

## 2. BrightFunded book + P6 vol-managed index CFDs (Gen127 P6, registered before)
| | 2022-26 | DEV 2022 | TEST 2023-24 | HOLD 2025-26 |
|---|---|---|---|---|
| bf | 2.252 | 1.154 | 3.45 | 1.545 |
| **bf + P6** | **2.302** | 0.461 | **3.691** | **1.849** |

- **P6 sleeve:** 0.34 / 1.67 / 0.86 (2020-22 / 23-24 / 25-26). Long US100 + US500 CFDs, 0.5 x 0.15 / 20-day vol each (cap 2x), 1 bp per side, swap-free.
- **Passes the strict bf rule** (2022-26 up, TEST and HOLD up).
- **Caveats:** equity beta; it weakens 2022 (a bear-market year).

## 3. Crypto (Gen133)
- **v7 = v6 + Gen109 ridge ML sleeve:** 2.534 / TEST 3.494 / HOLD 2.240 vs v6 2.458 / 3.435 / 1.901. **Passes the strict rule** (as Gen109).
- **v8** (+60-coin premium carry) and **bf-b + ridge** fail because 2023-24 falls.

## 4. Rejected along the way
- **Gen134 noise-area improvement round:** the selected variant fails both judgement periods (-0.20, -0.85).

## Next
- Build paper traders for v7, bf + P6, and the futures book, each with its own no-look-ahead self-test.
- The futures book needs a live data source for CME prices (prop platform feed, or a daily Databento pull).

## Update (later on 2026-10-20)
### Futures book: every selected sleeve is positive out of sample
| Sleeve | 2010-17 | 2018-22 | 2023-26 (unseen in the selection) |
|---|---|---|---|
| F3 month-end Treasury demand | 0.97 | 0.94 | 0.05 |
| F5 vol-managed long ES/NQ | 1.04 | 0.54 | 0.98 |
| G1 TSMOM 12m, 24 markets | 0.26 | 0.42 | 0.39 |
| P1 IBS reversal, index futures | 0.00 | 0.67 | 0.16 |
| A3 Treasury auction round trip | 0.40 | 0.47 | 0.26 |
| **Book** | 0.98 | 0.81 | **0.59** |

- **Book Sharpe by unseen year:** 2023 0.35, 2024 0.62, 2025 0.60, 2026 (to Sep) 0.83.

### Rounds that did not add a futures sleeve
- **Gen136:** basis-momentum, skewness, weekly reversal, bond trend, curve trend.
- **Gen137:** crypto sleeves on CME BTC/ETH (weekend closure and thin off-hours kill them; Topstep daily-flat is negative).
- **Gen138:** walk-forward ridge over 24 futures (0.44 / -0.31 / -0.53).

### Gen139: vol-managed long gold
- **Q1, in the bf book (on top of P6):** 2.302 -> **2.511**, TEST 3.69 -> 3.75, HOLD 1.85 -> 2.43. Passes the registered strict rule.
- **Q2, the same sleeve on 16 years of GC futures:** -0.04 / 0.28 / 1.12. It fails DEV: long gold lost in 2013-15, and its recent strength is the 2023-26 gold bull market.
- **Decision:** the bf test window (2022-26) is too short to separate a gold edge from the gold rally, so **gold runs as a shadow sleeve only**. P6 (equities) has 16-year support from F5 (1.05 / 0.55 / 0.98) and is the recommended bf improvement.
