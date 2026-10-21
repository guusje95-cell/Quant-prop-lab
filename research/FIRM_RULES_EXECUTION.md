# Firm rules and execution plan (2026-10-21; Gen323, `results/gen323.json`)

Rules come from web searches of third-party reviews and the firms' FAQ snippets (the firms' own sites cannot be opened from
the research cloud). **Everything marked "confirm" must be confirmed in writing by the firm's support before real money.**

## 1. HyroTrader (v8.6, Bybit USDT perps)

| Rule (as reported) | Applies to | v8.6 status | Action |
|---|---|---|---|
| Total notional of open positions <= **2x initial balance** (1st breach = warning, 2nd = funded account failed) | funded only (official FAQ) | at risk 2.0 the book is above 2x in **29% of hours** (median 1.66x, p99 3.39x) | funded: risk **1.5** + exposure cap 1.9x (see 3) |
| Total margin <= **25% of initial balance** | funded only | at 1.9x notional this needs average leverage >= 7.6x | set Bybit leverage to 10x on every pair (margin, not risk) |
| Max realised loss per position **3% of initial balance** ($6,000 on $200k), reviewed manually | all | at risk 2.0, 3 coin-days in 4.7 years above $6,000 (BTC, ETH; worst -$11.6k) | rare; at funded risk 1.5 smaller still. Confirm whether "position" = per coin |
| Evaluation: no single day > **40% of total profit** (profit distribution rule) | evaluation only | in 101 of 182 historical phase-1 walks the best day was > 40% at the +10% target day; compliant after a median **5 more days** | slows passing, does not fail it; nothing to change |
| Daily drawdown **5%** (FAQ) or **4%** (rules page) of initial balance, static from 00:00 UTC | all | modelled at 5% | **confirm**. At 4% the 2025-26 two-year mean net falls **$235k -> $193k** (p10 $140k -> $91k) |
| Max loss 10% static (2-Step) | all | modelled | - |
| Stop-loss within 5 minutes | older guides; reportedly **withdrawn** (2026) | the book uses no per-trade stops | **confirm** it is withdrawn |
| Martingale banned; hedging across two accounts banned | all | not used (one account per firm) | - |
| Bots / API / EAs: marketing says allowed; the terms reportedly ban them "except where expressly permitted" | all | the cascade sleeve places limit orders every hour (needs automation) | **confirm in writing** (see 4) |
| Tradable: Bybit USDT perps (700+) | all | 60 coins | **check the 40 extra coins are listed** |

## 2. BrightFunded (bf2.6, MT5 CFDs, swap-free)

| Rule (as reported) | v8.6/bf2.6 status | Action |
|---|---|---|
| Crypto leverage 1:5, indices 1:20 | modelled (1:5 crypto cap in the paper trader) | - |
| EAs allowed (not HFT / grid / tick scalping / arbitrage); copying between own accounts allowed | daily / 4-hourly / event trades: none of the banned types | - |
| No consistency rule; no minimum trading days funded; >= 1 trade per 30 days; trade open >= 1 minute | all trades are held hours to weeks | - |
| Weekend holding allowed (crypto trades when the instrument is open) | modelled | Monday index gaps count against drawdown (already in the backtest) |
| **Funded: no orders 5 minutes either side of high-impact news** (soft breach: that trade's profit is removed) | the R1 index entry is at 14:00 ET = **FOMC announcement time** (8 days a year) | on FOMC days place the R1 entry at 14:06 ET; everything else trades at 00:00 UTC, 16:00 ET or 4-hour boundaries, away from 8:30 ET data |
| Commission crypto 0.012% per side, indices $0; swap-free add-on removes all swaps (support-confirmed) | modelled | tick swap-free at purchase |

## 3. Execution plan for v8.6 (netting + no-trade band)

All sleeves are netted into ONE position per coin; the cascade (limit orders) and the Weiss expiry trade stay separate order
streams. Uniform 5 bp per trade + funding.

| Variant (risk 2.0 unless noted) | Sharpe 2022-26 / 2022 / TEST / HOLD | orders per day (mean / p90) | median order | gross > 2x |
|---|---|---|---|---|
| A every change traded | 3.158 / 1.58 / 4.02 / 3.16 | 62.6 / 71 | $366 | 29% of hours |
| B band $500 | 3.152 / 1.59 / 4.02 / 3.15 | 30.1 / 40 | $1,140 | 29% |
| C band $1,000 | 3.140 / 1.58 / 4.01 / 3.12 | 21.6 / 30 | $1,800 | 29% |
| D band $2,500 | 3.194 / 1.69 / 4.10 / 3.08 | 11.5 / 18 | $3,618 | 26% |
| F band $1,000 + cap 1.9x | 3.017 / 1.65 / 3.89 / 2.95 | 24.5 / 36 | $1,742 | 0.05% |
| **H risk 1.5 + band $1,000 + cap 1.9x** | **3.138 / 1.71 / 4.00 / 3.06** | **19.5 / 28** | $1,674 | **0%** |
| I risk 1.5 + band $1,000, no cap | 3.203 / 1.68 / 4.10 / 3.12 | 18.1 / 26 | $1,680 | 9% |

"Band": a coin is only traded when its target differs from the current position by more than the band (a target of zero
always closes). Netting alone saves cost (A 3.158 vs 3.110 sleeve by sleeve).

**Choice (registered rule: fewest orders with every period within 0.10 of A and gross <= 2x in >= 99.9% of hours): H.**
- **Challenge (no exposure cap):** risk 2.0, band $1,000 (about 22 orders a day; band $2,500 gives about 12 and was not worse).
- **Funded:** risk **1.5** (not 2.0 as Gen318 chose without knowing the 2x cap) + exposure cap 1.9x + band $1,000.
- Most orders are at 00:00 UTC (daily sleeves); trend 4h trades BTC / ETH / SOL at 4-hour boundaries; the cascade needs
  limit orders placed every hour (automation, or drop it: without the cascade v8.6 loses about 0.6 Sharpe, Gen313).

## 4. Questions to send (copy-paste)

**HyroTrader support:**
1. "On the 2-Step $200k: is the daily drawdown 4% or 5% of the initial balance, and is it static from 00:00 UTC equity?"
2. "Is the 2x initial-balance limit on total open notional (and the 25% margin limit) only for funded accounts, or also in the evaluation?"
3. "May I run my own automated strategy through the Bybit API (my own code, no third-party signals, no HFT), placing a few
   dozen orders a day? If yes, please confirm in writing."
4. "Is a stop-loss on every position still required, or was that rule withdrawn?"
5. "The 3% max loss per trade: is that per position (per coin), measured on realised P&L?"
6. "Are these USDT perps tradable on my account: (the 40-coin list in research/USER_TODO.md)?"

**BrightFunded support:**
1. "On the funded 2-Step Classic: which news events fall under the 5-minute rule, and is FOMC (14:00 ET) one of them?"
2. "Is there any limit on total open exposure or number of open positions for crypto CFDs?"
