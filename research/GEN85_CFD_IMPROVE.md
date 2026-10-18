# Gen85: improving the CFD book (2026-10-18)

- **Protocol:** `config/gen85_protocol.json`, registered before any number was computed. 8 trials.
- **Scripts:** `scripts/gen85_cfd.py` (tests) and `scripts/gen85_report.py` (stats and prop).
- **Costs:** CFD spreads 5 / 10 bp, swap 3.3 bp/day, no funding.

## Tests

| Test | DEV 20-22 | TEST 23-24 | HOLD 25-26 | CFD book 2022-26 (was 1.566) | Verdict |
|---|---|---|---|---|---|
| A1 Weiss expiry on all 11 CFD coins (replacement) | 0.06 | 1.59 | 0.11 | 1.50 | rejected: the altcoins dilute it; BTC/ETH Weiss is 0.46 / 1.64 / 0.63 |
| **B1 swap-aware C\*, thr 0.5 (DEV pick)** | **2.21** | **2.32** | **0.50** | **1.618** | **ADOPTED** |
| B1 thr 0 (current C\*) | 2.19 | 2.29 | 0.39 | 1.566 | reference |
| B1 thr 1.0 | 1.90 | 1.90 | 0.77 | 1.562 | not picked (worse on DEV) |
| B2 C\* long only / short only | - | - | - | - | no-op: C\* is already long-only |
| D1 trend 4h on 11 CFD coins, swap 3.3 | 0.60 | 1.11 | -0.41 | 1.20 | rejected |
| D1 same coins inside the swap-free book, swap 0 | 0.73 | 1.32 | -0.23 | 1.62 (was 1.81) | rejected |

**What B1 does:**
- Each day, any C\* coin weight smaller than half the average held weight is set to zero.
- The reason: a small position earns little but still pays the full swap and spread.
- Average gross falls from 0.117 to 0.112.

**Caveat:**
- B1 wins on DEV by only 0.02. The case rests mainly on TEST and HOLD, which both improved as the rule required.
- It is a small, honest gain, not a breakthrough.

## New CFD book (swap-aware C* + Weiss), 2022-26 at 15% vol

| Book | Sharpe | CAGR | Max DD | Positive months | 2022 / 23 / 24 / 25 / 26 (to Sep) |
|---|---|---|---|---|---|
| **NEW CFD book** | **1.62** | 26.0% | -16.2% | 49% | -7.4 / +57.3 / +50.3 / +13.6 / +20.7% |
| old CFD book | 1.57 | 25.1% | -16.0% | 47% | -8.9 / +58.7 / +49.1 / +11.6 / +20.3% |
| swap-free book (Gen83, swap-free accounts only) | 1.81 | 29.8% | -12.8% | 67% | |

## Prop results ($100k, 2 years, bootstrap 500 paths, adopted setting 1.5 / 1.0 / 60%)

| Firm | Pass rate | Days to pass | Mean net | Unlucky 10% | P(profit) | Old book mean / p10 |
|---|---|---|---|---|---|---|
| FTMO 2-Step | 70% | 105 | $26.3k | $3.2k | 94% | $25.7k / $3.0k |
| FundedNext Stellar 2-Step | 65% | 100 | $27.7k | $4.0k | 94% | $26.7k / $3.3k |
| BrightFunded 2-Step Classic | 67% | 110 | $26.1k | $3.0k | 94% | $25.6k / $2.8k |

The crypto-firm v5 is unchanged at Sharpe 2.28. B1 applies to the CFD route only, because Binance perps have no swap.
