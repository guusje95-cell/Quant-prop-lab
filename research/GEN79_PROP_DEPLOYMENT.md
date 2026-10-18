# Gen79: per-firm prop deployment optimisation

- **Protocol:** `config/gen79_protocol.json`.
- **Script:** `scripts/gen79_prop_opt.py`.
- **Grid:** `results/gen79_grid.csv` (64 cells x 7 firms).
- **Choices:** `results/gen79_choice.csv`.
- **Trials added:** 7.

**What was varied:** risk in the challenge, risk once funded, and our own daily stop (as a share of the firm's daily limit). The strategies are unchanged.

**How the cell is picked:**
- Bootstrap paths are drawn only from 2022-24.
- The cell must meet minimum safety: P(profit) >= 95% (crypto firms) / 88% (CFD firms), and unlucky 10% >= 0.
- Scores are smoothed over neighbouring cells.

**How it is verified:** bootstrap paths drawn only from 2025-26, data never used for the pick.

| Firm | Pick (challenge / funded / stop) | Adopted? | 2025-26 mean net: pick vs default | 2025-26 unlucky 10% | 2025-26 P(profit) | Full 2022-26 mean: pick vs default |
|---|---|---|---|---|---|---|
| HyroTrader 1-Step | 1.25 / 1.0 / 60% | **yes** | **$26.8k vs $17.8k** | $8.8k vs $7.8k | 97.3% vs 99.0% | $41.6k vs $26.8k |
| HyroTrader 2-Step | 1.5 / 1.0 / 50% | **yes** | **$27.6k vs $14.9k** | $11.5k vs $5.3k | 98.7% vs 97.3% | $42.5k vs $24.2k |
| SizeProp 1-Step | 1.0 / 1.0 / 60% | no (P(profit) -3 pts) | $18.8k vs $15.6k | $4.0k vs $5.8k | 95.3% vs 98.3% | keep 1.0 / 0.6 / 50% |
| Crypto Fund Trader 1-Phase | 1.0 / 1.0 / 50% | **no (worse on 2025-26)** | $11.9k vs $14.5k | -$4.0k vs $4.1k | 83% vs 94% | keep 1.0 / 0.6 / 50% |
| FTMO 2-Step (CFD book) | 1.5 / 1.0 / 60% | **yes** | **$19.8k vs $10.5k** | $1.8k vs -$0.6k | 92.0% vs 89.3% | $26.0k vs $15.3k |
| FundedNext Stellar (CFD book) | 1.5 / 1.0 / 60% | **yes** | **$20.9k vs $11.3k** | $3.0k vs $0.5k | 94.7% vs 90.7% | $26.8k vs $16.1k |
| BrightFunded Classic (CFD book) | 1.5 / 1.0 / 60% | **yes** | **$19.7k vs $10.5k** | $1.1k vs -$0.5k | 92.3% vs 89.7% | $26.0k vs $15.3k |

## Reading
- **The main finding: funded accounts were run too cautiously.** Every pick uses funded risk 1.0 instead of 0.6.
  - Once funded there is no fee at risk, only the profit split.
  - A higher risk level raises payouts more than it raises the chance of losing the account.
  - The challenge risk goes up as well (1.25-1.5) at firms with 2-step or static limits.
- **The rule rejected the risky picks where they did not hold:**
  - **CFT:** its 6% trailing loss limit punishes higher risk; on 2025-26 the pick was clearly worse.
  - **SizeProp:** the pick lost too much safety.
- **Caveat 1, live performance:** these picks assume the backtest edge. If live Sharpe is lower (we plan for about 1.3-1.7 instead of 2.25), higher risk levels lose more often.
- **Caveat 2, challenge risk 1.5 is the edge of the grid.** Start at the lower end of the picks for the first accounts, e.g. 1.25 / 0.8 / 60%. Move to the full picks once the paper and early live results match the backtest.
