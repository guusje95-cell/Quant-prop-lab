# Gen63: more crypto-only ideas (2026-10-15)

**Protocol:** `config/gen63_protocol.json`, registered before running. **Scripts:** `scripts/gen63_crypto.py`, `scripts/gen63_check.py`.

| Idea | DEV | TEST | HOLD | 2023+ | 2022 | corr C* | Verdict |
|---|---|---|---|---|---|---|---|
| I1 C* on 20 coins (vs 10) | 1.86 (vs 2.24) | 1.94 (vs 2.23) | 0.44 (vs 0.53) | 1.34 (vs 1.53) | | | rejected: worse than 10 coins |
| I2 cascade with risk-based sizing | -1.05 | 0.93 | 0.58 | 0.77 (vs 1.19) | | | rejected |
| I3 short-squeeze continuation | -0.35 | 1.09 | 0.67 | 0.86 | -10% | 0.12 | near-miss (DEV < 0) |
| I4 premium carry with trend-aligned legs | 0.94 | 1.01 | 0.97 | 0.99 (vs 1.01) | | | rejected: not better |
| **I5 daily dip-buy in uptrends** | 0.40 | 0.94 | 0.62 | 0.79 | -8% | 0.11 | passes its own criteria, **fails the final check** |
| **I6 4-hour breakout trend (BTC/ETH/SOL, long-short)** | 0.80 | 1.43 | 0.45 | 0.94 | **+5%** | 0.34 | near-miss (HOLD 0.45 < 0.5, corr 0.34 > 0.3) |

**I5 robustness:**
- 2x costs: 0.76.
- Neighbours (2023+): k=2.0 0.59, k=3.0 0.92, MA50 0.93, MA200 0.30, hold 2 0.75, hold 5 0.65, max 5 open 0.89.
- HOLD is fragile: -0.11 to 0.75 across neighbours.

**Pre-registered final check** (equal-risk portfolio, 2022–26, 15% vol):

| Portfolio | Sharpe 2022–26 | Sharpe 2023+ | Positive months | Max DD | 2022 |
|---|---|---|---|---|---|
| Current: C* + premium carry + cascade | **1.56** | 1.98 | 61% | -17.2% | -4.7% |
| + I5 dip-buy | 1.48 | 2.08 | 60% | -16.8% | -9.3% |
| + I3 squeeze (near-miss) | 1.43 | 1.97 | 60% | -14.4% | -9.0% |
| + I6 4h trend (near-miss) | **1.69** | 2.00 | **65%** | -15.5% | **+0.6%** |
| + I5 + I6 | 1.72 | 2.17 | 60% | **-11.3%** | -4.3% |

## Verdict

- **Under the strict rules nothing is added:** I5 lowers the 2022–26 Sharpe, and I6 narrowly misses its own criteria.
- **I6 is the only idea that addresses the bear-year weakness.** It earns in 2022 and adds +0.13 Sharpe to the portfolio.
- **I6 goes on the forward-test list** next to the three crypto sleeves. It is only promoted if it holds up live.
