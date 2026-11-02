# v9.8.1 - relative crowding 6 fix: before / after validation (2026-11-02)

Approved by the user on 2026-11-02 with conditions 1-7 and a clean 56-day gate. Strategy v9.8 (logic, parameters, sizing, risk model,
frozen settings, scale) unchanged; the change is recorded in `config/paper_v98.json` (changes, 2026-11-02, "v9.8.1").

## Root causes
1. **Calendar gap at 00:00 UTC (scripts/basket_live.py).** The daily calendar `DAYS` ended at the day of `END` (= the last completed hour).
   In the 00:00 run the next-hour book needs the new day, which was outside `DAYS`, so the daily and 3-day versions (4 of 6) of the sleeve
   were 0 for that hour; at 01:00 they were back. Reproduced on research data: cutoff 2026-09-20 00:00 gave only the 8-hour part
   (BTC +0.0034, ETH -0.0140, ...); after the fix it equals the full-data run (BTC -0.0047, ETH -0.0634, SOL +0.0432, ...).
2. **Duplicate timestamps in the live ratio updater (src/qpl/live/binance_public.py).** Binance repeats bars across pages; when one
   endpoint repeats and another has an extra bar, the column merge raised `cannot reindex on an axis with duplicate labels`. This failed on
   every paper run since 2026-10-27 (143 DATA_PARTIAL events), so the live long/short ratios were never written and the daily signal ran on
   values carried forward from the research pack's last day (2026-09-30).

## Fix
- `_days_for(index)`: the calendar reaches the day of the hours being positioned (adds only that row; positions still come from weights
  decided at earlier closes). Research run unchanged: relative crowding sleeve max |new - stored| = **1.7e-18**, sum 0.462459 both.
- `update_ratios`: duplicates dropped per endpoint before the merge; `ratio_status()` reports the newest ratio per coin.
- Paper run: `RC_DATA` event every run (newest timestamp per coin), `DATA_STALE` if > 2 h old or missing. Monitoring only.
- On the first post-fix run the updater back-fills the ratios (Binance keeps 30 days), i.e. from about 2026-10-04.

## Tests and look-ahead
- `tests/test_v98_rc_fix.py` (6 tests): duplicate timestamps (**the old updater fails exactly as on the PC**, the new one passes), missing
  data (the strategy's own rule unchanged: a missing weight row stays 0), stale data flags, the 00:00 transition (**old code: 0 for all
  6 coins; new code: equals the full-calendar result**), a value known only at the close of day D does not change day D's positions,
  calendar unchanged inside the research range. Full suite: 211 passed.
- Paper truncation selftest (27 cutoffs incl. 00:00 / 01:00 boundaries, delistings, listings): **PASSED**, max |difference| 6.9e-18.
- `check_v98_freeze.py`: broken by the edited files (as designed) -> change logged -> manifest rewritten -> OK.

## Before / after (paper 2026-10-30 16:00 .. 2026-11-02 07:00, $200k, risk 2.0)
| | before (affected) | after (expected) |
|---|---|---|
| Live ratio data | not updated since 2026-10-27; signal on 2026-09-30 values | updated every run; back-filled ~30 days; staleness logged |
| RC positions 00:00 -> 01:00 | 4/6 of the sleeve closed at 00:00 and re-opened at 01:00 every day | continuous (research behaviour) |
| RC notional in hours 00-01 | **$190,301 a day** (other hours $816 a day) | about the sleeve's real daily change (research: 0.38 x its gross a day) |
| All rebalance notional | **$299,282 a day = 1.50x equity** | without the flip $108,980 a day = 0.54x (research net turnover at this risk: 0.54x) |
| Extra cost of the flip | **~$114 a day = 0.057% of equity a day** (~21% of the expected +0.27% a day) | 0 |
| In the frozen ledger P&L? | **No**: the ledger is computed an hour later with the full calendar, so it shows the research positions and costs; the flip and its costs existed only in the orders (what a live bot would have traded) | ledger and orders agree |

Backtest-versus-paper: with the fix the remaining known differences are the documented ones (Binance funding instead of Bybit funding,
model half spreads, R1 limit orders only in the bot). The stale ratio signal of the affected period also changed the sleeve's target
positions versus a correct live run; its P&L effect is not recoverable (the frozen ledger is kept as recorded).

## Gate
- History since 2026-10-30 is kept unchanged and flagged **'affected (pre-fix)'**.
- The **clean validation period** starts at the first post-fix run on the PC (first `RC_DATA` event); clean days count from the next full
  UTC day. status.md shows both: the gate on all days, and the clean gate (x of 56). v9.8 is fully validated only after **56 clean days**.
