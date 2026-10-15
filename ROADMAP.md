# Roadmap (from 2026-10-15)

Goal: 5-7 validated, mutually unrelated strategies, giving 2-4 per firm type (crypto, CFD/forex, futures). They run through bots on several prop firms, for steady monthly payouts. Realistic target: a live portfolio Sharpe of about 2.

Where we are:
- 1 validated strategy: C* + BTC leads (crypto).
- Candidates: BTC evening window, Nasdaq breakout, futures trend/carry.
- A tested prop simulator for 20 firm programmes.
- All tests for the incoming data written down in advance: Gen57 (Binance), Gen59 (re-tests on Dukascopy and Databento), Gen60 (literature queue).

## Phase 0: data (now)
| Who | What |
|---|---|
| You | Let `get_all_free_data.bat` finish (Binance + premium + Dukascopy 1/2/3), push `research_data` (push Binance as soon as its pack is written) |
| You | Databento: free account (no card), API key in `setx`, `get_databento_check_cost.bat`, then `get_databento_download.bat`, push |
| You (optional) | ChatGPT paper search (prompt in HOME_TODO.md), send PDFs |
| Claude | Done: test plans fixed in advance (config/gen57, gen59, gen60) |

## Phase 1: crypto (Binance pack arrives)
- Gen57 T1-T10:
  - evening window with maker fills;
  - funding and positioning;
  - liquidation reversal;
  - intraday breakout;
  - clean basis;
  - C* with real funding, perp execution, 08:00 UTC rebalance and the 4 overlays.
- Gen60 B1-B6:
  - intraday BTC/ETH trend, long and short;
  - long-short evening/night window;
  - CTREND weekly factor;
  - cascade reversal;
  - opening-minute taker flow;
  - crowding overlay.
- **Gate:** at least 1 new crypto strategy that passes (TEST Sharpe >= 0.8 after costs, correlation with C* < 0.3, holdout >= 0.5).
- **Output:**
  - the final C* version (with honest costs);
  - the crypto portfolio;
  - prop sims per crypto firm.

## Phase 2: CFD firms (Dukascopy arrives)
- Gen59 re-tests with frozen settings on fresh 2023-2026 data:
  - noise-area breakout, European open, overnight, turn-of-month;
  - semivariance trend, multi-asset trend;
  - pairs;
  - C* on BTC/ETH CFDs;
  - Q-learning.
- Gen60 D1-D4:
  - FX fix W-pattern;
  - gold Asia/London split;
  - breakout on DAX/FTSE/Nikkei;
  - month-end FX overlay.
- Real spreads by hour from the ask data.
- **Gate:** 2+ strategies that pass, so a CFD account can hold 3-4 strategies.

## Phase 3: futures firms (Databento arrives)
- Gen60 C1-C5:
  - ES European open after a falling close;
  - NQ/ES breakout with a volatility filter;
  - crude oil on inventory-report days;
  - multi-asset end-of-day momentum;
  - Nasdaq opening-range breakout.
- Gen59: futures trend/carry and curve strategies to 2026, intraday C* on CME BTC.
- **Gate:** 2+ intraday strategies that fit futures-firm rules (flat before the close, trailing loss limit).

## Phase 4: portfolios and firm choice
- Per firm type, combine the validated strategies with equal risk.
- Per firm:
  - challenge and funded risk;
  - daily stop;
  - payout timing;
  - number of accounts and staggering.

  Chosen on older data, confirmed on the test period and the hourly/minute replay.
- Firm ranking by net profit, chance of profit and months with a payout. Dashboard and Lab updated.
- **Output:** a concrete plan per firm (which strategies, which risk settings, how many accounts), with expected results and bad-case results.

## Phase 5: execution and paper trading
- C* paper trading can start **now**. I'll upgrade the signal script to C* + BTC leads.
- Bot per platform, with a paper/demo mode:
  - Bybit / Binance / Hyperliquid API;
  - MT5;
  - TopstepX API.
- Safety guards on every bot:
  - own loss stop below the firm's limit;
  - maximum position size;
  - kill switch;
  - logging;
  - daily summary sent to your phone.
- 4-8 weeks on demo/testnet. **Gate:** live fills and P&L match the backtest within tolerance; no execution errors.
- You check each firm's rules on automation, number of accounts and capital caps with their support.

## Phase 6: first challenges (your decision and your money)
- 2-3 firms, 1 account each, about $100k each. Budget roughly EUR 1-2k for fees including re-buys.
- You buy and switch the bots on; I never place real trades or pay for anything.
- Expect 2-5 months to pass; payouts start after that.

## Phase 7: scale up and maintain
- More firms and accounts, staggered (crypto, CFD, futures), up to each firm's cap. Use the scaling plans.
- Every month:
  - live vs backtest per strategy;
  - replace strategies that decay, using the same pre-registered process;
  - test new papers.
- Year 1 realistic: about $0.4-0.8M funded. Year 2: $1.5-2.5M if everything holds.
- From a few thousand per month on serious amounts: tax advice (income, possibly KvK registration).

## If things go worse than hoped
- No new strategy passes: run C* alone at crypto firms (lower income, fewer months with a payout) and keep searching with new data and papers.
- Live results clearly below the backtest for 2-3 months: pause, analyse, and only restart with a cause found and fixed.
- A firm changes its rules or does not pay: stop there and move capital to other firms (that is why we spread).

## Rough timeline
| When | Milestone |
|---|---|
| Weeks 0-1 | data in; C* paper trading starts |
| Weeks 1-4 | phases 1-3 research (depends on data arrival) |
| Weeks 4-6 | phase 4 portfolios + firm plan; bots built |
| Weeks 6-12 | demo / paper trading |
| Months 3-4 | first challenges |
| Months 5-7 | first payouts |
| Year 2 | scale to 6-8 firms |
