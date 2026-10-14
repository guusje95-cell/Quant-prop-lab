# Gen55: which prop firm? Each firm's own rules and costs (2026-10-14)

Protocol: `config/gen55_protocol.json`, registered before any result was computed. Script: `scripts/gen55_firms.py`. Raw output: `results/gen55_firms.csv` and `results/gen55_dev_grid.csv`.

## What was simulated

**Strategy.** C\* + BTC leads (Gen53), not re-tuned.

**Firms.** 17 crypto prop programmes from the user's comparison, plus an FTMO swap stress test. Presets are in `src/qpl/lab/propfirms.py`. Each firm is modelled with its own:

- profit targets per phase, daily loss and max loss (static or trailing), minimum days, split, refund;
- trading fee per side and swap per day on open notional (Breakout 0.033%/day);
- leverage cap: Breakout 5× BTC/ETH and 2× others; FundedNext 1:1. Neither binds at these risk levels, because gross exposure is at most 0.9× and usually 0.1–0.2×;
- daily reset hour: SizeProp 20:00 UTC; FTMO, FundedNext and BrightFunded about 22:00 UTC (midnight CE(S)T);
- payout minimum ($100 at HyroTrader) and first-payout delay (FundedNext 21 days, then every 14).

**Replay.** Real Binance hourly prices, 2022-01 to 2026-10. The strategy rebalances at 00:00 UTC; the firm's day runs from its own reset hour.

**Account set-up.** One account, up to 5 challenges, 24 months, one simulated trader started every 5 days.

**Two settings per firm:**

- **Baseline:** challenge 1.0×, funded 0.4×, no stop. This is the same for every firm, so it is a fair comparison.
- **DEV pick:** the best of 24 risk settings on 2018–2022 daily data with that firm's costs.

**Assumptions.** Items not in the user's data are labelled ASSUMED in each preset's note:

- Fees: Breakout $999 (one blog, all three plans); BrightFunded $495 (aggregators; One-Step unknown); CFT 2-Phase $660 (aggregators).
- Payout cadence: 14 days for HyroTrader and BrightFunded, 30 days for Breakout, 7 days for SizeProp.
- Split: 80% everywhere.
- Spread/slippage: about 2 bp on exchange firms, about 5 bp on FTMO crypto CFDs.
- FTMO swap is unknown, so the stress row uses Breakout's rate.

## Results (hourly replay 2022–2026, $100k accounts unless stated)

| Firm | Setting | Risk ch/fd | Stop | Pass | Funded | Fees | Net avg | Net typical | Net p10 | P(profit) | Months w/ income |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HyroTrader Two-Step $200k | baseline 1.0/0.4 | 1/0.4 | - | 64% | 98% | $1,018 | **$24,033** | $23,774 | $8,760 | 98% | 22% |
| HyroTrader Two-Step $200k | DEV pick | 1.5/0.6 | 75% | 46% | 100% | $2,612 | **$22,669** | $19,566 | $16,396 | 99% | 21% |
| SizeProp One-Step $100k | DEV pick | 1.5/0.6 | 75% | 43% | 98% | $2,751 | **$18,704** | $19,793 | $9,874 | 98% | 24% |
| HyroTrader One-Step $100k | DEV pick | 1.5/0.6 | 75% | 46% | 100% | $1,829 | **$17,018** | $13,928 | $9,970 | 100% | 19% |
| HyroTrader Zero-Step $100k | DEV pick | 1.5/0.6 | 75% | 32% | 100% | $3,420 | **$15,149** | $12,246 | $9,475 | 98% | 20% |
| Breakout One-Step Classic $100k | DEV pick | 1.5/0.6 | 75% | 29% | 100% | $3,126 | **$14,419** | $11,810 | $8,370 | 99% | 17% |
| Crypto Fund Trader 2-Phase $100k + weekly payouts + 90% split | DEV pick | 1/0.6 | - | 70% | 98% | $1,563 | **$14,061** | $12,206 | $7,428 | 98% | 20% |
| HyroTrader One-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 57% | 100% | $1,111 | **$13,731** | $12,316 | $7,201 | 100% | 21% |
| FTMO 2-Step $100k | DEV pick | 1.5/0.6 | 75% | 49% | 100% | $1,305 | **$13,710** | $10,691 | $8,626 | 97% | 21% |
| Crypto Fund Trader 2-Phase $100k + weekly payouts + 90% split | baseline 1.0/0.4 | 1/0.4 | - | 70% | 98% | $945 | **$13,040** | $11,678 | $4,664 | 98% | 22% |
| FTMO 2-Step $100k (swap stress 3.3bp/day) | DEV pick | 1.5/0.6 | 75% | 47% | 100% | $1,291 | **$12,777** | $9,728 | $7,728 | 99% | 20% |
| BrightFunded Two-Step Bright $100k | baseline 1.0/0.4 | 1/0.4 | - | 67% | 100% | $538 | **$12,598** | $11,996 | $5,563 | 97% | 22% |
| FundedNext Stellar 2-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 68% | 98% | $573 | **$12,469** | $11,363 | $5,997 | 98% | 23% |
| Crypto Fund Trader 2-Phase $100k | DEV pick | 1.5/0.6 | 75% | 50% | 100% | $1,420 | **$12,303** | $8,912 | $6,145 | 99% | 15% |
| FTMO 2-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 64% | 98% | $612 | **$12,105** | $11,967 | $5,212 | 98% | 21% |
| BrightFunded Two-Step Classic $100k | baseline 1.0/0.4 | 1/0.4 | - | 63% | 98% | $520 | **$12,095** | $11,996 | $5,563 | 98% | 22% |
| HyroTrader Two-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 64% | 98% | $608 | **$12,008** | $11,887 | $4,380 | 98% | 22% |
| FundedNext Stellar 2-Step $100k | DEV pick | 1.5/0.6 | 75% | 58% | 100% | $1,417 | **$11,933** | $9,890 | $7,472 | 99% | 19% |
| Crypto Fund Trader 1-Phase $100k | baseline 1.0/0.4 | 1/0.4 | - | 33% | 100% | $1,394 | **$11,557** | $10,082 | $5,568 | 98% | 22% |
| Crypto Fund Trader 1-Phase $100k | DEV pick | 0.75/0.4 | - | 56% | 100% | $1,085 | **$11,284** | $10,082 | $5,141 | 97% | 21% |
| Crypto Fund Trader 2-Phase $100k | baseline 1.0/0.4 | 1/0.4 | - | 70% | 98% | $675 | **$11,197** | $10,091 | $3,770 | 97% | 22% |
| HyroTrader Two-Step $100k | DEV pick | 1.5/0.6 | 75% | 46% | 100% | $1,561 | **$11,172** | $9,783 | $7,990 | 99% | 21% |
| BrightFunded Two-Step Classic $100k | DEV pick | 1.5/0.6 | 75% | 46% | 100% | $1,316 | **$11,084** | $9,746 | $8,756 | 97% | 21% |
| FTMO 2-Step $100k (swap stress 3.3bp/day) | baseline 1.0/0.4 | 1/0.4 | - | 61% | 98% | $617 | **$10,734** | $10,014 | $3,953 | 97% | 22% |
| SizeProp One-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 44% | 100% | $2,096 | **$9,729** | $7,718 | $4,263 | 98% | 23% |
| Breakout Two-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 35% | 100% | $1,579 | **$9,332** | $7,720 | $2,189 | 96% | 17% |
| SizeProp Degen $100k | baseline 1.0/0.4 | 1/0.4 | - | 24% | 96% | $2,261 | **$9,141** | $10,397 | $4,005 | 94% | 25% |
| HyroTrader Zero-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 51% | 100% | $2,152 | **$8,198** | $7,036 | $4,627 | 98% | 19% |
| BrightFunded One-Step $100k | baseline 1.0/0.4 | 1/0.4 | - | 20% | 100% | $1,631 | **$8,130** | $5,419 | $2,237 | 100% | 20% |
| Breakout One-Step Pro $100k | DEV pick | 1.5/0.6 | 75% | 25% | 77% | $4,102 | **$8,067** | $8,370 | $-4,995 | 75% | 12% |
| BrightFunded Two-Step Bright $100k | DEV pick | 1.5/0.6 | 75% | 33% | 100% | $1,939 | **$7,986** | $8,345 | $3,559 | 97% | 15% |
| BrightFunded One-Step $100k | DEV pick | 0.5/0.4 | - | 57% | 97% | $842 | **$7,720** | $7,809 | $4,246 | 97% | 20% |
| SizeProp Degen $100k | DEV pick | 1/0.25 | 75% | 37% | 97% | $1,366 | **$6,944** | $6,360 | $3,711 | 96% | 25% |
| Breakout One-Step Classic $100k | baseline 1.0/0.4 | 1/0.4 | - | 48% | 100% | $2,214 | **$6,588** | $5,182 | $2,448 | 98% | 15% |
| Breakout Two-Step $100k | DEV pick | 1.5/0.6 | 75% | 26% | 100% | $3,978 | **$5,754** | $6,067 | $1,388 | 94% | 15% |
| Breakout One-Step Pro $100k | baseline 1.0/0.4 | 1/0.4 | - | 38% | 100% | $3,642 | **$2,616** | $3,143 | $-735 | 74% | 13% |

## Conclusions

1. **The cheap two-steps with a fee refund are the most robust choice.** Baseline nets cluster at about $12–12.6k per account over 2 years, for about $520–610 in fees, with P(profit) of about 98% in this period:
   - BrightFunded Two-Step Bright;
   - FundedNext Stellar;
   - FTMO;
   - HyroTrader Two-Step;
   - BrightFunded Classic.

   Pass rates are 63–70%, and they hardly depend on the risk setting.

2. **HyroTrader One-Step gives the most per $100k account:**
   - baseline $13.7k;
   - aggressive DEV pick (1.5×/0.6× with a daily stop at 75% of the limit) $17.0k, with p10 still $10k.

   **HyroTrader Two-Step $200k** gives about 2× the $100k numbers ($24k) for only 1.7× the fee.

3. **SizeProp One-Step works only with the aggressive setting:** $18.7k at the DEV pick but $9.7k at the baseline. That spread is a fragility warning. **SizeProp Degen** (2% daily / 3% max) is too tight for this strategy: pass rate 24–37%.

4. **Breakout ranks last.** Its swap of 0.033%/day on open positions costs about 1–2% a year at this exposure. Combined with 3% daily / 5–6% max limits, pass rates fall to 25–48%. Pro has a negative p10. Its prices are also unverified, so the dollar figures are uncertain, and Breakout bans third-party strategies.

5. **Picking a firm does not fix consistency.** Months 7–24 with net income stay at 12–25% for every firm and setting. The strategy's profit is lumpy (Gen54), and payout frequency cannot change that. Steadier months still need the uncorrelated strategies 2–4.

6. **The DEV picks almost always land on the edge of the grid** (1.5×/0.6× + stop). That beats the baseline only at firms with expensive one-step challenges, and loses at the cheap two-steps. Not a general rule.

## Caveats

- Only about 4.8 years of hourly data. The 2-year programmes started every 5 days overlap heavily, so this is effectively about 2 independent periods, one of them the 2023–24 bull market. P(profit) of 98% is far too optimistic as a forecast. Gen53's point-in-time check suggests a realistic Sharpe of about 1.4–1.5, not 1.78.
- Check each firm's algo / EA / copy-trading policy before buying. C\* is one rebalance a day and can be placed by hand, but rules differ.
- Prices and rules change. Each preset's note lists what was assumed.
