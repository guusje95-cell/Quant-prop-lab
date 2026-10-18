# Gen96: validation and risk audit of the CFD book (2026-10-18)

- **Book audited:** C\* swap-aware + Weiss expiry + deleveraging bounce, at CFD costs; Sharpe 1.80 for 2022-26.
- **Scripts:**
  - `scripts/gen96_pit_dump.py` and `scripts/gen96_pit_compare.py` (part A);
  - `scripts/gen96_risk.py` (parts B-D);
  - `scripts/gen96_delay_split.py` (part B per sleeve).
- **Results:** `results/gen96_*.csv`.
- This is a validation run. No strategy or parameter was changed because of it.

## A. Look-ahead (point-in-time truncation test)

- **Method:** each signal was recomputed in a fresh process with the data physically cut at a cutoff (`QPL_CUTOFF`). This is the mechanism the paper trader uses.
- **Cutoffs:** 2023-03-15, 2024-06-10, 2025-05-20, 2026-01-12, 2026-08-03.
- **Comparison:** each cut run was compared with the full-data signal for every row that was decidable before its cutoff.

| Signal | Rows compared (all cutoffs) | Rows different |
|---|---|---|
| C\* (swap-aware) daily weights | 13,701 | **0** |
| Deleveraging bounce daily weights | 5,866 | **0** |
| Weiss expiry hourly positions | 224,784 | **0** |

**No future data leaks into any signal.**
- The portfolio layer (monthly risk weights from past days only, and a vol target shifted by one day) was already verified at 8 cutoffs in the v5 paper-trading self-test.
- **Control:** feeding the book its positions 24h early (deliberate look-ahead) lifts the Sharpe to 2.59, so the test can detect leakage.

## B. Execution delay

| Late by | Whole book | Only C\* late | Only Weiss late | Only bounce late |
|---|---|---|---|---|
| 0h | 1.80 | 1.80 | 1.80 | 1.80 |
| 1h | 1.49 | 1.77 | **1.57** | 1.74 |
| 2h | | 1.76 | **1.07** | 1.84 |
| 3h | 1.04 | 1.73 | 1.14 | 1.77 |
| 6h | 0.94 | 1.79 | 1.00 | 1.79 |
| 24h | 0.82 | 1.54 | 1.01 | 1.67 |

- **C\* and the bounce are robust to late execution:** 1-6h late costs little.
- **Weiss is a 2-hour trade by design.** Executed 1h late its own Sharpe falls from 1.11 to 0.80; 2h late it is 0.21.
- **Rule for live trading:** enter Weiss at 08:00 UTC sharp on the last Friday of the month. If that is missed, skip that month rather than enter late.

## C. Risk

| Measure | Value |
|---|---|
| Block bootstrap (20-day blocks, 2,000 paths), 2-year Sharpe | 5% / 50% / 95%: **0.69 / 1.80 / 2.96** |
| Bootstrap 2-year max DD at 15% vol | median -9.4%, 5% worst -15.4%, 1% worst -18.8% |
| Bootstrap P(2-year return < 0) | 0.5% |
| Deflated Sharpe probability (Bailey & Lopez de Prado), N = 30 / 700 / 7,000 trials | **0.98 / 0.81 / 0.57** |
| Daily skew / kurtosis | +3.2 / 45 (positive skew: trend and bounce winners) |
| Worst day at 15% vol | -5.8% (2026-02-01); next worst -5.2% (2022-11-09, FTX) |
| Sharpe by year | 2022 0.57, 2023 2.93, 2024 3.22, 2025 1.23, 2026 1.44 |
| Rolling 6-month Sharpe | minimum -0.61; below 0 in 8% of windows |

**Deflated Sharpe:** about 640 trials are logged in this project's protocols, and Gen52's grid alone held about 5,900 highly correlated variants. At the most conservative count (7,000) the probability that the true Sharpe is above zero is 57%. At the protocol count (about 700) it is 81%.
- The edge is likely real, but the true Sharpe is probably below the backtest's 1.80.
- **Plan for 1.0-1.5 live.**

### Crash windows (book at 15% vol)

| Window | Book | BTC |
|---|---|---|
| LUNA 2022-05-05..20 | -0.6% | -26% |
| 3AC/Celsius 2022-06-10..20 | 0.0% | -32% |
| FTX 2022-11-06..15 | **-6.2%** | -21% |
| SVB 2023-03-09..13 | +0.9% | +11% |
| Yen carry 2024-08-02..07 | -0.9% | -16% |
| Oct-10 liquidations 2025-10-09..12 | +2.4% | -7% |

### Cost stress (2022-26 Sharpe)

| Scenario | Sharpe |
|---|---|
| base | 1.80 |
| swap 6.6 bp/day | 1.71 |
| 2x spread | 1.54 |
| 2x spread + swap 6.6 | 1.45 |

### Daily-loss risk (share of days with an intraday dip beyond the threshold)

| Book scale | dip < -2% | dip < -3% (the 60% stop) | dip < -5% (FTMO limit) | Worst intraday |
|---|---|---|---|---|
| 1.0 (15% vol) | 1.2% | 0.6% | 0.1% | -5.7% |
| 1.5 (challenge setting) | 2.9% | 1.2% | **0.5%** (about 1.7 days a year) | -8.6% |

**Prop implication:**
- At 1.5x, roughly one day in 200 drops more than 5% intraday. The 60% stop fires first on most of those days, but a single hour can gap through it.
- The prop simulator books that gap: the stop fills at the first hourly close below it.
- So the 83-85% pass rates already include this risk. **Do not raise the challenge scale above 1.5.**

## D. Parameter maps (descriptive only, nothing selected)

**Deleveraging bounce, sleeve Sharpe 2022-26:**

| OI drop \ hold days | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 6% | 0.17 | 0.38 | 0.15 | 0.18 |
| 8% | 0.17 | 0.31 | 0.20 | 0.17 |
| **10%** | 0.45 | **0.66** | 0.65 | 0.54 |
| 12% | 0.30 | 0.49 | 0.67 | 0.52 |
| 14% | 0.01 | 0.29 | 0.47 | 0.12 |

**Book Sharpe 2022-26:**

| OI drop \ hold days | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 6% | 1.15 | 1.38 | 1.32 | 1.33 |
| 8% | 0.75 | 1.51 | 1.51 | 1.39 |
| 10% | 1.67 | **1.80** | 1.80 | 1.47 |
| 12% | 1.62 | 1.55 | 1.62 | 1.62 |
| 14% | 1.62 | 1.62 | 1.44 | 1.46 |

**Reading the grid:**
- Every cell is positive, and a 10-12% ridge holds with 2-3 day holds.
- **The registered setting (10%, 2 days) is the best cell.** It was registered in Gen89 before the grid existed, but a best-cell result usually overstates the future.
- **Realistic expectation for the sleeve:** about 0.4-0.5, not 0.66. The book without the bounce is 1.62; a realistic book is about 1.65-1.75.

**C\* swap-aware threshold (C\* / book):**

| Threshold | C\* | Book |
|---|---|---|
| 0 | 1.21 | 1.76 |
| 0.25 | 1.21 | 1.76 |
| **0.5** | 1.28 | 1.80 |
| 0.75 | 1.28 | 1.81 |
| 1.0 | 1.12 | 1.74 |

This is a flat region, not a spike.

## Verdict

- **Clean:** no look-ahead, robust to cost stress and to late execution of C\* and the bounce, and good behaviour in crashes. FTX is the worst at -6%.
- **Discounts to apply:**
  - the trial count (deflated Sharpe);
  - the bounce being at the best grid cell.
- **Realistic live CFD Sharpe: about 1.2-1.6.**
- **Operational rule:** Weiss must be executed on time.
