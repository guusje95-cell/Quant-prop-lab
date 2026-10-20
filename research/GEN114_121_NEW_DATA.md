# Gen114-121 (2026-10-20): Databento futures, Binance extra coins, BrightFunded breadth

All tests were pre-registered before the data arrived (Gen114, Gen115, Gen80, Gen112) or before the result was computed (Gen121).

## Data checks (Databento CME hourly, 28 roots, 2010-06 .. 2026-09)
- Two fixes before any test result was used:
  - **Roll bars:** the return now comes from the contract actually held (the old front), not the new one.
  - **CL in April 2020:** negative prices, so no percentage return is computed for those bars.
- **Carry bug, found and fixed on the first T1 run:** Databento's volume-ranked "second" contract (.v.1) is sometimes the expiring one, right after a roll (6% of hours on ES, 17% on ZN). Carry now orders the two contracts by listing date (near/far). Result before the fix: 0.29 / 0.03 / -0.28; after: 0.04 / -0.16 / -0.41. Both fail.
- **Large hourly moves** are real weekend reopen gaps: the OPEC war (2020-03-08), the BTC weekend rally (2019-10-27), winter natural gas.

## Futures (stand-alone rule: DEV 2010-17 > 0, TEST 2018-22 >= 0.5, HOLD 2023-26 >= 0.3)
| Test | DEV | TEST | HOLD | Verdict |
|---|---|---|---|---|
| T1 trend+carry, 24 markets | 0.04 | -0.16 | -0.41 | rejected |
| T1 at $100k, whole micro contracts (report) | 0.30 | -0.22 | -0.75 | - |
| T2 intraday momentum (last hour) | -3.53 | -2.08 | -1.71 | rejected (costs) |
| T3 overnight drift ES/NQ | -0.22 | 0.54 | 0.56 | rejected (DEV < 0) |
| T4 T1 signal in-session only | -0.76 | -0.93 | -1.30 | rejected |
| U1 EIA crude day | -0.08 | 0.08 | -0.30 | rejected |
| U2 opening-hour range breakout | -1.03 | -0.70 | -0.73 | rejected |
| U3 overnight-intraday reversal | -1.47 | -0.13 | 0.39 | rejected |
| U4 bond-equity lead | -0.96 | -0.85 | -0.19 | rejected |
| U5 cross-sectional momentum 12-1 | 0.50 | 0.23 | 0.36 | rejected (TEST) |
| U6 commodity curve carry | 0.22 | -0.83 | 0.42 | rejected |
| U7 FX month-end fix | 0.59 | -0.51 | -0.13 | rejected |
| U8 gold Asia-session drift | 0.48 | -0.69 | 0.59 | rejected |

- **Trend alone, gross (diagnostic only):** it follows the industry pattern (2010 +1.9, 2012 -1.3, 2014 +1.0, 2020 +2.0, 2022 +1.8, 2023-25 negative).
- **Carry is noisy in this setup:** rates and livestock calendar spreads swing a lot, which hurts T1.
- **No futures book can be formed.**

## CME bitcoin signals (crypto rule into v6 and bf)
- **T5 CME basis momentum:** perp 0.12 / 0.33 / 1.10. It lowers v6 2.46 -> 2.31 and bf 2.25 -> 2.06. Rejected.
- **T6 "CME gap fill" (178 weekends):** perp -0.02 / -2.34 / 0.31. Rejected; the popular gap-fill belief does not hold.

## Binance extra coins (40 more USD-M perps)
### Gen80: premium carry breadth (frozen Gen61 rule)
| | sleeve 2020-22 / 23-24 / 25-26 | sleeve 2023-26 | v6 2022-26 | v6 TEST / HOLD | v5 2022-26 |
|---|---|---|---|---|---|
| 20 coins (current) | 0.87 / 0.68 / 1.15 | 0.87 | 2.458 | 3.44 / 1.90 | 2.275 |
| 60 coins | 1.25 / 0.84 / 2.52 | 1.53 | **2.539** | **3.14** / 2.39 | 2.336 |
| 54 coins with >= $20m/day | 1.56 / 1.09 / 2.47 | 1.67 | 2.626 | 3.22 / 2.32 | - |

- **Robustness (`results/gen80_check.json`):**
  - Better than 20 coins in every year 2020-2026.
  - At 2x costs: 1.15 / 0.68 / 2.31, against 0.79 / 0.55 / 0.98 for the current sleeve.
  - Leave-one-out on the top 5 contributors (SNX, INJ, ENJ, BCH, HBAR): TEST 0.62-1.06, HOLD 2.21-2.54.
- **Verdict:**
  - It passes its own registered Gen80 rule (2023-26 and HOLD >= current, v5 2022-26 up).
  - It **fails the stricter standing book rule** (since Gen105), because v6 book TEST falls 3.44 -> 3.14.
  - Not adopted into v6. Forward-test candidate.

### Gen80 cascade part: strict-limit cascade on 60 coins
| | sleeve 2020-22 / 23-24 / 25-26 | 2023-26 | v6 2022-26 |
|---|---|---|---|
| 20 coins (current) | 0.40 / 1.73 / 0.79 | 1.30 | 2.458 |
| 60 coins, max 3 open | 0.23 / 1.54 / 0.21 | 0.90 | 2.318 |
| 60 coins, max 5 open (registered variant) | 0.12 / 1.59 / 0.12 | 0.91 | 2.249 |

**Verdict:** rejected. More coins dilute the cascade: the extra coins' events are weaker, and they take the 3 slots.

### Gen112: deleveraging bounce on all altcoins
- **G1 sleeve:** -0.30 / 1.27 / 0.83 (DEV 2022 negative, as on the 20-coin alts before). Rejected.
- **G2 hit table:** 4,888 episodes on extra coins, 2-day mean +0.74%, 50% positive. The mean replicates the pack alts (+0.71%, 52%), but it is noisy.

### Gen121: premium carry breadth in the BrightFunded book (42 BF-listed coins)
| | bf 2022-26 | bf DEV / TEST / HOLD | sleeve 2023-26 |
|---|---|---|---|
| current (11 coins) | 2.252 | 1.15 / 3.45 / 1.55 | 0.92 |
| 42 coins | **2.414** | 1.51 / **3.18** / 2.09 | 1.43 |
| 42 coins, 2x spreads | 2.176 (current at 2x: 2.049) | 1.34 / 2.93 / 1.84 | - |

- **Verdict:** same as v6. Better book overall and in HOLD, but book TEST falls, so it fails the strict rule. Not adopted; forward-test candidate.

## Bottom line
- 16 new trials. Nothing passes the strict book rule.
- **Premium carry on more coins** is the strongest new candidate on both books: 2022-26 +0.08 (v6) and +0.16 (bf), HOLD +0.5.
- Its 2023-24 book Sharpe falls, so under our own rules it stays a candidate for a forward (paper) test, not an adoption.

## Shadow paper tests started (2026-10-20)
- **v6b** (`config/paper_v6b.json`): v6 with premium carry on 60 coins.
- **bf-b** (`config/paper_bfb.json`): the bf book with premium carry on 42 BrightFunded coins.
- **Backtest reference files** were made by the paper trader itself (`results/cache_v6b_final.parquet` 2.539, `cache_bfb_final.parquet` 2.414), identical to the research numbers.
- **Breadth mode trades only premium carry on the new coins:** C* stays on the original 11 CFD coins in bf-b. Without that, C* would have picked up BNB.
- **Decision rule:** after >= 56 days, a shadow book replaces its main book only if it is not worse over the same hours and it reconciles.
