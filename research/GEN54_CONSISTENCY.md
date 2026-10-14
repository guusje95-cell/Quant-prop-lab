# Gen54: toward consistent monthly payouts

## Where we stand

C* + BTC leads (Gen53), 103 months:
- Positive months: 50%.
- Median month: 0.0%.
- The 10 best months produce 77% of all profit.
- Longest losing run: 5 months.

This is the normal shape of trend-following, and it fits prop payouts poorly.

The share of positive months is set mainly by the Sharpe ratio (monthly normal approximation):

| Annual Sharpe | Positive months |
|---|---|
| 1.0 | 61% |
| 1.5 | 67% |
| 2.0 | 72% |
| 3.0 | 81% |
| 4.0 | 88% |

**Goal:** stack 2–4 uncorrelated edges toward a combined Sharpe of about 3.

## G54a: prop account structure (script `scripts/gen54_account_structure.py`)

**Setup:** C* + BTC leads, challenge 1.0× / funded 0.4×, replayed on hourly prices 2022–2026, 24-month programs, each account with a budget of 5.

| Structure | Avg net | P10 net | Months 7–24 with net income | Avg income / month |
|---|---|---|---|---|
| 1 × CFT | $11,998 | $6,295 | 22% | $602 |
| 3 × CFT, same day | $35,993 | $18,884 | 22% | $1,806 |
| 3 × CFT, staggered 0/2/4 months | $32,680 | $10,545 | 25% | $1,754 |
| 1 × FTMO | $12,687 | $4,380 | 22% | $634 |
| 1 CFT + 1 FTMO | $24,685 | $10,675 | 28% | $1,236 |
| 2 CFT + 2 FTMO, staggered | $46,158 | $19,067 | 31% | $2,415 |
| 6 accounts (3 CFT + 3 FTMO), staggered monthly | $65,342 | $24,494 | 33% | $3,539 |

**What this shows:**
- More accounts multiply income.
- Staggering and mixing firms raise the share of months with income only from 22% to 33%, because every account trades the same signals.
- A payout needs a new equity high. Steady monthly income therefore needs a second return stream, not just more accounts.

## G54b: hour-of-day effect (Quantpedia: BTC strongest 21:00–23:00 UTC, Gemini 2015–2022)

**Protocol:** `config/gen54_protocol.json`. Long 21:00–23:00 UTC daily, OKX perps hourly.

| | 2020–22 Sharpe (annual return) | 2023–26 Sharpe (annual return) |
|---|---|---|
| BTC, before costs | 1.53 (+30%) | **1.91 (+24%)** |
| BTC, 2 bp/side (maker) | 0.78 | 0.77 |
| BTC, 5.5 bp/side (taker) | −0.53 | −1.23 |
| 10 majors, before costs | 1.11 | 1.63 |
| 10 majors, 2 bp | 0.54 | 0.86 |

- **Verdict under the pre-registered rule (taker cost): NOT PASSED.**
- **But the edge before costs persists out of sample, which makes it a strong candidate if it can be executed with maker (limit) orders.**
- **At 2 bp:**
  - 60% of months are positive.
  - Monthly correlation with C* is 0.14.
  - C* + 0.5× this overlay raises positive months from 49% to 60%.
- **Next step:** check maker fill rates with 1-minute data (`python -m qpl.lab.binance_vision all`). An overlay (adding to an existing C* position only during the window) also cuts trading costs.

## Data request (user, on PC)

- **Command:** `get_binance_data.bat` (Windows) or `get_binance_data.sh`.
- **What it downloads:** 1-minute futures candles, open interest / long-short ratios and funding for 20 coins from data.binance.vision. Free, no account.
- **Output:** a compact pack in `research_data/binance/`. Commit and push it.
- **What it enables:**
  - intraday candidates (hour-of-day with maker fills, liquidation reversal, intraday momentum);
  - open-interest and funding signals.
