# Gen105: demand composite (Coinbase + Korean premium) (2026-10-19)

- **Protocol:** `config/gen105_protocol.json`, registered before any number. 1 trial.
- **Scripts:** `scripts/gen105_demand.py` and `scripts/gen105_check.py`.
- **Book:** the BrightFunded CFD book (paper 'bf').
- **Question:** does the composite replace the Coinbase premium sleeve?

## A data-timing error, found by the checks

Yahoo stamps each USD/KRW daily bar at London midnight. In summer that is 23:00 UTC of the previous calendar day. The first run normalised the timestamp to a UTC date, so in summer:
- "the previous day's FX close" was really the same day's close;
- that close comes in at about 22:00-23:00 UTC, the same hour as the 23:00 UTC kimchi reading.

That is not clean point-in-time data. The FX series is now **dated by its London day and lagged one full day**, and only that strict version is used.

**Gen102's kimchi results (P2) used the same mis-dated FX and are optimistic.** Strict kimchi-only sleeve: 0.36 / 0.90 / 1.70, against 0.67 / 1.12 / 2.40 before.

| Version | Sleeve DEV 20-22 | TEST 23-24 | HOLD 25-26 | Book 2022-26 | Book TEST / HOLD |
|---|---|---|---|---|---|
| Coinbase premium (current sleeve) | 0.72 | 1.33 | 0.70 | 2.25 | 3.45 / 1.55 |
| composite, mis-dated FX (first run, **invalid**) | 1.25 | 1.88 | 1.56 | 2.45 | 3.57 / 2.04 |
| **composite, strict FX (valid)** | **1.20** | **1.37** | **1.11** | **2.30** | **3.33 / 1.87** |

**Strict-FX checks (descriptive):**

| Check | Result |
|---|---|
| Threshold 0.75 / 1.25: book | 2.41 / 2.23 |
| Placebo (30-day blocks shuffled, 60 runs): sleeve 2020-26 | mean -0.03, 95th percentile 0.68; actual 1.17, **p < 0.02** |
| Entry 1h / 4h late (mis-dated run) | sleeve 1.36 / 1.20 |
| BTC only / ETH only (mis-dated run) | 1.29 / 1.33 |

## Verdict: NOT adopted (the pre-registered rule fails on one point)

**What passes:**
- The sleeve beats the Coinbase sleeve on DEV, TEST and HOLD.
- The book rises from 2.25 to 2.30.
- Book HOLD rises from 1.55 to 1.87.

**What fails:**
- **Book TEST falls from 3.45 to 3.33.** The rule requires book TEST and HOLD not to fall, so the composite is not adopted.

**Watchlist:**
- The composite is a strong candidate (placebo p < 0.02).
- Re-test it with fresh data in 2027, or as a shadow sleeve in paper trading.
