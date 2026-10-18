# Gen89-90: new CFD ideas, and the deleveraging bounce (2026-10-18)

- **Protocols:** `config/gen89_protocol.json` (5 trials) and `config/gen90_protocol.json` (1 trial), both registered before any number.
- **Scripts:** `scripts/gen89_cfd.py`, `scripts/gen89_check.py`, `scripts/gen90_books.py`.
- **Function:** `crypto_sleeves.delev_bounce()`.
- **Chart:** `results/gen90_books.png`.

## Gen89 tests (CFD costs; DEV 2020-22, or 2022 for open-interest data)

| Test | DEV | TEST 23-24 | HOLD 25-26 | CFD book after (1.618) | Verdict |
|---|---|---|---|---|---|
| H1 NFP-day crypto momentum | -0.18 | -0.61 | 0.09 | 0.81 | rejected |
| H2 weekend reversal | -0.61 | -0.22 | -0.22 | 0.91 | rejected |
| H3 US500 below 100-day MA -> C\* half size | 2.27 (C\* 2.21) | 2.09 (2.32) | 0.43 (0.50) | 1.40 | rejected |
| **H4 deleveraging bounce** | **0.70** | **1.01** | **0.61** | **1.80** | **PASSED** |
| H4 variant, 5% OI drop | -0.15 | 1.40 | -0.01 | 1.49 | variant |

**H4 rule:**
- **Signal (checked once a day, at 23:55 UTC):** BTC or ETH open interest (Binance, USD value) fell more than 10% over the past 24 hours, AND the price also fell over those 24 hours.
- **Trade:** go long that coin at 00:00 UTC for 2 days.
- **Size:** 0.5 per coin.
- **Why it might work:** forced liquidations and deleveraging push the price below fair value, and it bounces back afterwards. This is the daily version of the cascade sleeve; correlation with C\* is 0.03 and with the cascade 0.07.

**Data fix before the result was used:**
- The Binance open-interest file has stretches of exact zeros (data gaps, e.g. 2022-03-07).
- A zero could fake a 100% drop. Zeros are now treated as missing, carrying the last valid value forward.
- With the fix, DEV fell from 0.98 to 0.70. TEST and HOLD were unchanged. The numbers above are after the fix.

## Robustness (descriptive, no selection)

| Check | Result |
|---|---|
| Nearby settings | 2022-26 positive for all: threshold 7.5 / 12.5 / 15% = 0.32 / 0.44 / 0.36; hold 1 / 3 / 5 days = 0.45 / 0.65 / 0.28 |
| Weak spots | DEV 2022 at 7.5% is -0.14; hold 5 fails HOLD |
| BTC only / ETH only | 0.70 / 0.54 |
| Entry 1h / 4h later | 0.62 / 0.55 |
| 2x spread | 0.60 |
| Trade count | 70 episodes, 51% hit rate, +84 bp per episode, t = 2.2 |
| Every year positive | 2022 +21%, 2023 +7%, 2024 +11%, 2025 +9%, 2026 +6% (sum of episode returns) |
| **Weakness: fat right tail** | without the 5 best episodes the 2022-26 Sharpe drops from 0.6 to 0.2 |

**Interpretation:**
- It is a "catch the rebound after a flush" trade. Most trades are small and a few are large.
- That is the nature of the effect, but it means the realised Sharpe will be noisy.

## Gen90 books (2022-26, at 15% vol)

| Book | Sharpe | TEST / HOLD | CAGR | Max DD | Positive months | 2022 / 23 / 24 / 25 / 26 |
|---|---|---|---|---|---|---|
| **NEW CFD book (swap-aware C\* + Weiss + deleveraging bounce)** | **1.80** | 3.09 / 1.31 | 29.5% | **-11.8%** | 56% | +8 / +46 / +54 / +19 / +17% |
| Gen85 CFD book | 1.62 | 3.00 / 1.24 | 26.0% | -16.2% | 49% | -7 / +57 / +50 / +14 / +21% |
| **NEW swap-free book (+ deleveraging bounce)** | **2.07** | 3.41 / 1.36 | 34.8% | **-10.0%** | 70% | +10 / +64 / +63 / +14 / +23% |
| Gen83 swap-free book | 1.81 | 3.29 / 1.12 | 29.8% | -12.8% | 67% | |

## Prop ($100k, 2 years, bootstrap 500 paths)

| Book / firm | Setting | Pass | Mean net | Unlucky 10% | P(profit) |
|---|---|---|---|---|---|
| NEW CFD book, FTMO 2-Step | 1.5 / 1.0 / 60% | 83% | **$31.3k** | $10.1k | 98% |
| NEW CFD book, FundedNext Stellar | 1.5 / 1.0 / 60% | 85% | **$32.3k** | $10.6k | 99% |
| NEW CFD book, BrightFunded Classic | 1.5 / 1.0 / 60% | 83% | **$31.2k** | $10.3k | 98% |
| (Gen85 CFD book, same firms) | 1.5 / 1.0 / 60% | 65-70% | $26.1-27.7k | $3.0-4.0k | 94% |
| NEW swap-free book, FundedNext swap-free | 1.5 / 1.0 / 60% | 82% | **$41.8k** | $17.3k | 99% |

## Crypto-firm v5 test (perp costs: 5 bp taker plus funding)

- **H4 alone:** DEV 2022 0.76, TEST 1.04, HOLD 0.65, corr C\* 0.04. It **passes** the standing crypto rule.
- **v5 + H4:** Sharpe 2.28 -> **2.46** (TEST 3.35 -> 3.44, HOLD 1.68 -> 1.90).
- **Candidate v6** = v5 + deleveraging bounce.
- v5 paper trading stays frozen. Switching to v6 is a separate decision; the live feed already downloads open interest (openInterestHist).
