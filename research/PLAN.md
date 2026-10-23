# Plan (2026-10-21)

Books: v8.6 (crypto, HyroTrader 2-Step $200k, Bybit bot allowed) and bf2.6 (CFD, BrightFunded 2-Step Classic $200k swap-free, MT5 EA).
Backtest Sharpe 3.11 / 2.83; planning Sharpe (deflated) about 1.8 / 1.5. Rules and execution: research/FIRM_RULES_EXECUTION.md.

## Phase 1 - validate (now to about week 4-8)
- User: keep paper_v86 and paper_bf26 running; run paper_v86_share.bat and paper_bf26_share.bat about once a week.
- User: push Bithumb (get_bithumb_core.bat) and the point-in-time universe (get_binance_pit.bat); optional get_deribit_options.bat.
- User: check that the 40 extra coins are tradable on Bybit; confirm with HyroTrader that the same strategy on several own
  accounts is fine (later, before scaling).
- Claude: run the pre-registered tests when the data arrives: Gen321 (survivorship; v8.5/v8.6 withdrawn if it fails),
  Gen277 (Bithumb), Gen309 (options). Reconcile the paper results each week.
- Gate to phase 2: Gen321 passes, >= 4 weeks of paper with z > -1 vs the backtest and no reconciliation / data errors.

## Phase 2 - build and test the execution (about 1-2 weeks)
- Claude: Bybit API bot for v8.6 (netting, $1,000 band, minute equity check, 2.5% daily stop, funded 1.9x cap, risk 2.0 / 1.5)
  and MT5 EA for bf2.6 (same + news-window guard); keys and passwords stay on the user's PC.
- User: test on a free demo (Bybit demo if available from NL; any MT5 demo), compare orders with the paper trader.

## Phase 2b - access check (before buying)
- Written answer from HyroTrader: can a Dutch resident use the Bybit-connected Two-Step (Bybit is limiting EEA access since 2026-06)?
  If not: does the Hyro platform allow an own API bot, with the same coins, fees and funding? If neither: v8.6 at another
  crypto prop firm (rules to be checked as for HyroTrader) or BrightFunded only.

## Phase 3 - first account
- User decides and buys the first v8.6 account at whichever of HyroTrader / CFT (Bybit route) confirms NL access + bot in writing
  (equal in Gen330/332). Challenge risk 2.0, funded risk 1.5, daily stop 2.5%. No MT5 route without swap-free (Gen331).
- Expectation (planning, deflated): about $90k over 2 years for this account, bad case about $20k, small chance of a net loss.

## Phase 4 - scale up
- After the first payout and live results in line with paper: add BrightFunded (bf2.6). HyroTrader allows ONE account per program
  and prohibits mirror trading across accounts (terms v1.16), so more capital comes from other firms, each checked first. Both books are about the same bet (correlation 0.8): more accounts = more money, not more safety.
- Order (Gen332, by what each adds to the planning bad case): HyroTrader / CFT -> the other of the two -> BrightFunded (bf2.6)
  -> MyFundedPerps -> Propr (only if research_data/hyperliquid shows most of the 60 coins). All five: planning mean about $326k
  over 2 years, p10 about $89k, fees at risk about $25-30k, P(total loss) about 1.5%.
- Research then: an edge that does NOT move with crypto (not a higher backtest Sharpe).
