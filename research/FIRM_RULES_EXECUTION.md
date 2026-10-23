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

## 5. Update 2026-10-21: BrightFunded support answers (written, for the funded $200k 2-Step Classic on MT5)
- **News rule:** high-impact (red-folder) events of the Help Center calendar (Forex Factory times). FOMC decisions / statements
  affect **all USD instruments, crypto USD pairs included**. No execution (opens, closes, limit / stop / SL / TP fills) from
  5 minutes before to 5 minutes after (FOMC 14:00 ET -> 13:55-14:05 ET; a separately listed press conference has its own window).
  Positions opened earlier may be held. TPs on trades held >= 48 h are exempt. **Soft breach: that trade's profit is removed.**
  -> book impact: crypto rebalances happen at 00:00 UTC and trend trades at 4-hour UTC boundaries (never at 8:30 / 10:00 / 14:00 ET);
  the R1 index entry (14:00 ET) and any other order must skip red-folder windows: the EA needs a news-calendar guard.
- **Exposure:** no numerical cap on crypto notional or on the number of positions; margin (1:5) is the limit. The risk team's
  overexposure review treats correlated same-direction crypto positions as one position (judged after the evaluation).
  -> the carry sleeves are long-short (direction-neutral); the directional part (C*, trend, ridge, delev bounce, Coinbase
  premium) is what they would look at.
- **EAs:** allowed in challenge and funded; hourly limit orders without martingale / HFT / signals "does not sound like a grid";
  no pre-approval (risk review after the evaluation).
- **Swap-free:** +10% of the fee at checkout, all instruments incl. index and crypto CFDs, no replacement charge; only at purchase.
- **Commissions:** crypto 0.012% per side, indices 0 (model uses 1 bp per side on indices: conservative).
- **Weekend holding allowed;** drawdown on real-time equity incl. floating P&L; **daily limit = 5% of the initial balance measured
  from the HIGHER of balance or equity at the daily rollover**; max loss static 10%; gaps through a limit count.
  -> **NEW RISK:** MT5 "balance" only moves when trades close. Our book holds most positions for days to weeks, so a floating
  loss at the rollover leaves balance above equity and the day's floor is set from the (higher) balance: e.g. floating -3% at
  the rollover leaves only 2% room that day. Mitigation for the EA: shortly before the rollover, close and reopen positions
  that are in a floating loss (realises the loss, balance = equity on them; cost = spread on those positions only).

## 6. HyroTrader: published rules (read by the user from the official pages, NOT a support answer)
- Daily drawdown 5% of initial balance, static from 00:00 UTC equity, evaluation and funded (FAQ and rules page).
- 2x notional / 25% margin: funded only. Stop-loss not required. 3% max loss per trade (definition unclear).
- **Automation on Bybit: NOT established.** HyroTrader's own relaunch material says its platform agents cannot trade on Bybit;
  permission for a self-written Bybit API bot needs a written answer. Until then plan for MANUAL execution.

| v8.6 variant (research, sleeve-level) | Sharpe 2022-26 / 2022 / TEST / HOLD |
|---|---|
| full (needs automation: hourly cascade limit orders) | 3.110 / 1.54 / 3.97 / 3.11 |
| without the cascade (no hourly orders) | 2.893 / 0.92 / 3.79 / 3.06 |
| manual: without cascade and trend 4h (one batch a day + monthly Weiss) | **2.613** / 0.31 / 3.63 / 3.08 |
| manual, daily batch only | 2.445 / 0.25 / 3.32 / 3.00 |

## 7. Update 2026-10-21 (later): HyroTrader bots ALLOWED; Gen324 balance/equity simulation
- **HyroTrader official FAQ (found by the user):** "Can I create a Bybit API key to trade on a different platform?" and "Are trading
  bots allowed during the challenge and funded phase?" -> yes: an API key on the Bybit (demo) account may run your OWN bot;
  third-party signal bots, copied strategies and copy trading are prohibited. **v8.6 can therefore run in full (3.11, incl. the
  hourly cascade limit orders).** The manual variants in section 6 are only a fallback.
- **Gen324 (MT5 accounting, bf2.6, risk 2.0; `results/gen324.json`):**
  - A (reference = equity, our model): 67 daily stops; B (BrightFunded: max(balance, equity) at the rollover): 89 stops, same
    breaches, Sharpe not lower (2.488 vs 2.458 in this stop simulation). Gap between balance and equity at the rollover: mean $278,
    p95 $1,822, above $4,000 on 10 days in 4.7 years. **The balance rule costs little for this book.**
  - C (close and reopen floating losers before every rollover): costs $193k over 2022-26, Sharpe 1.78. **Rejected: do not do this.**
  - **Gap risk:** with an HOURLY 2.5% stop, single hours that jump past the 5% daily limit: bf2.6 at risk 2.0 on 2025-10-10
    (the October 2025 liquidation crash), v8.6 at risk 2.0 on 2023-03-22 and 2024-03-05; none at risk 1.5 in either book.
    The prop simulations already count these as failures (to_daily_stop keeps the hourly path's worst point).
  - **Bot requirement:** monitor equity continuously (every minute, not every hour) and flatten at the 2.5% daily stop; that
    catches most of these hours midway. A crash within minutes can still pass the limit: that is the residual risk of risk 2.0.

## 8. Bybit reality check (Gen327, 2026-10-23)
- All 60 v8.6 coins trade on Bybit (min order $5). Bybit funding + taker 5.5 bp + half spread + $1,000 band: 3.027 instead of 3.158.
- Thin books (42 of 60 coins under $500 at the best price): the bot must place the daily / carry rebalances as **post-only limit
  orders** (Bybit maker fee 0.02%), re-quoted for a few hours, and only cross the spread at the end of the window; trend, Weiss and
  the daily stop use market orders. A deeper order-book measurement (50 levels, cost of a $2k / $5k order) can be added to
  get_bybit_check.bat before the bot is built.

## 9. Update 2026-10-23: HyroTrader terms v1.16 (effective 2026-09-29) and help pages, as read by the user's assistant (published documents, NOT a support answer)
- **Netherlands:** not on HyroTrader's blocked-country list, but **Bybit announced (2026-06-29) a progressive limitation of Bybit Global
  services for EEA residents, incl. the Netherlands.** HyroTrader's FAQ names its own platform ("Hyro") as the route for people
  who cannot use Bybit. -> OPEN, decisive: can a Dutch resident use the Bybit-connected Two-Step; if not, does the Hyro platform
  offer API access for an own bot, the same 60 USDT perps, maker / taker fees and funding?
- **Fees (Bybit, VIP 0, USDT contracts): maker 0.0200%, taker 0.0550%** - exactly the Gen327 assumptions.
- **No 3%-per-trade rule found for the Two-Step:** 5% daily drawdown (floor = start-of-day equity - 5% of the initial balance,
  equity incl. floating P&L and fees, reset 00:00 UTC) and 10% max loss. The per-coin cap from Gen328 is therefore not needed for
  this rule (still optional).
- **Multiple accounts: section 4.5 - one account per program type at a time; section 10.2(b) - coordinated multi-account
  trading and mirror trading are prohibited; 10.2(e) - automating your own strategy is allowed.** -> at HyroTrader plan for ONE
  account with v8.6; scaling must come from other firms (with their own rules checked), not from copies at HyroTrader.
- Still to confirm in writing: Dutch access / Hyro-platform API; whether running v8.6 at HyroTrader and bf2.6 (a related crypto
  book) at BrightFunded counts as "coordinated multi-account trading" (the wording targets HyroTrader's own accounts).
- Follow-up (same day, published documentation, not a support answer): the **Hyro platform** trades USDT perpetuals on live Bybit
  market data; **automation is offered through Hyro's MCP integration** (not established: whether it can place / amend / cancel limit
  and market orders, read positions and equity every minute, and its rate limits); Hyro fees and funding treatment not published.
  Trading a related strategy at ANOTHER prop firm is allowed if the accounts are run independently and never used to hedge,
  arbitrage or offset each other. -> v8.6 at HyroTrader + bf2.6 at BrightFunded is fine in principle (confirm in writing).
- Follow-up 2 (published docs): Hyro MCP trading is live (2FA + agent token, trading access separate from read access, native platform
  only, 700+ USDT perps on live Bybit data); NOT published: the MCP tool schema (amend / cancel orders, positions / equity fields and
  refresh), rate limits, Hyro's own fees and its funding treatment. Section 10.2(m): only offsetting / hedging against external
  positions is prohibited; independent trading elsewhere is allowed. -> these open points go to HyroTrader support in writing.

## 10. Other crypto prop firms for v8.6 (Gen329, 2026-10-23; published pages / reviews, NOT support answers)
| Firm | Rules used | Bot / API | Fit | Open points (ask before buying) |
|---|---|---|---|---|
| Crypto Fund Trader 2-Phase | 5% daily (balance 00:05 UTC), 10% static, 8% / 4%, 80% split | EAs allowed; MT5, Match-Trader or Bybit route | **best alternative**; risk 2.0 challenge / 1.5-2.0 funded | NL accepted? Bybit route available for NL? which of the 60 coins are tradable; MT5 crypto swaps and commissions; multi-account / copy rules |
| Propr 2-Step | 5% daily, 8% TRAILING | API-first (Python SDK), copying between own accounts allowed | reserve; risk 1.0 only | Hyperliquid coin list vs the 60 coins; 2x leverage cap on non-majors (v8.6 gross can exceed it); fees |
| MyFundedPerps | 3% daily, 3/5/6% static | REST / CLI / MCP | not recommended (daily limit too tight) | NL in the 30 restricted countries? |
| Breakout | 3% daily | bots banned | excluded | - |
| SizeProp | - | frontend-only automation | excluded | - |
Risk per firm is the only setting changed: at a 3% daily limit the daily stop moves to 1.5%, at a trailing 8% the risk drops to 1.0. Strategy parameters stay as v8.6 (re-fitting them per firm would be fitting to rules, not to markets).

## 11. Web research 2026-10-23 (published pages and reviews, NOT support answers; container cannot open the firms' own sites)
- **Crypto Fund Trader:**
  - Platforms: MT5 / Match-Trader (simulated), plus a Bybit route on Bybit sub-accounts. On the Bybit route, Bybit's own fees and funding apply, there is no markup, and the API connection must not be modified.
  - MT5 crypto commission: 0.0325% per side.
  - Swaps on MT5 are charged on positions open at 00:00 UTC. The rate is unknown, and Gen330 shows it decides the MT5 route.
  - EAs are allowed. Banned: HFT, tick scalping, arbitrage, news-scalping and multi-account reverse EAs.
  - Copying between accounts: Ascend accounts may not copy each other; Break accounts may copy only during the evaluation.
  - Allocation cap: $300k per user combined. The $200k 2-phase costs about $1,150–1,250. Split 80% (90% as an add-on).
  - No published country list. The Bybit route from the NL is likely affected by Bybit's EEA restriction (since 2026-06-29), so ask.
- **Propr (official rulebook as quoted by reviews):**
  - Classic 2-Step $100k: $749; targets 5% then 10%; 5% daily loss.
  - 8% trailing drawdown on equity (open profit raises the high-water mark), which never rises above the starting balance and resets after a payout.
  - Equity-based checks; a breach closes the account.
  - Altcoins 2x leverage; BTC/ETH 5x or 10x (sources conflict).
  - Python SDK `propr_sdk`, API at api.propr.xyz/v1. Bots allowed; uncustomised shared bots may be flagged.
  - Aggregate cap $300k.
- **MyFundedPerps:**
  - Select / Prime / Signature at $10k–100k. Signature: 10% target, 3% daily of the starting balance from midnight New York, 6% static.
  - $100k Signature costs $696 (launch price).
  - The NL is not on the restricted lists found (30 countries).
- **HyroTrader routes:**
  - Bybit: Bybit's terms restrict EEA users.
  - Tealstreet: the FAQ conflicts on whether country restrictions apply.
  - CLEO: Binance prices, no country restrictions, B-booked. CLEO's documentation says API trading is not supported at the moment.
  - So the NL + bot route at HyroTrader is the Hyro platform with MCP (section 9) or CLEO if API access is added. Ask.
- **Hypernova (Hyperliquid):** single step up to $200k; 3–5% daily and 6–8% static by tier; developer API "coming soon"; only self-written bots allowed. Not usable yet.
- **Bitfunded:** bot policy conflicts between sources. Not considered.
- **CFD firms (FTMO and others):** about 30 crypto CFDs, leverage about 1:3.3, swaps charged and no swap-free option. Weaker than BrightFunded (swap-free) for bf2.6.

## 12. Consequences of Gen331-333 for the platform choice (2026-10-23)
- **CFD platforms without swap-free are excluded for v8.6.** Measured normal MT5 crypto swaps are about -49% a year (median), which wipes out the book. CFT therefore only via its Bybit route, unless CFT confirms a swap-free option.
- **The bot must trade within the hour:** 1 hour late costs 0.18 Sharpe.
- **OKX prices reproduce the backtest exactly**, so any venue with normal perp prices (Bybit, OKX-like, Hyperliquid) is fine. The coin list and costs decide, not the venue.
- **Propr / Hyperliquid:** run `get_hyperliquid_check.bat` (public data, no wallet) to get the real coin list, leverage, funding and spreads. 60 coins -> 3.11; 51 coins -> 2.87.
- **Order type (Gen337b):** each hourly trade is first posted as a limit order at the previous hour's close for 15 minutes, then sent as a market order. This gives about +0.04 Sharpe over always using market orders; measure the real fill rate in the first live weeks.
