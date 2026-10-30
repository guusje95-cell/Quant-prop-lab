# Quant Trading Hub: user guide

Research-driven, largely autonomous operations layer on top of Quant Prop Lab. **Paper and research only: there is no live
trading adapter, `live_trading_enabled` is locked to false, and no job can spend money, place orders or read credentials.**

## Start it (Windows, on the PC that runs the paper trader)
1. `git pull`
2. **`hub_start.bat`**: creates / migrates the database `hub_data/hub.sqlite`, ingests everything (experiments, protocols, results,
   paper ledgers, strategies, prop rules, data catalogue), then runs the background worker. Leave the window open.
   Without a window: run **`hub_task_scheduler.bat`** once; Windows then runs one worker pass every 15 minutes.
3. **`hub_dashboard.bat`**: opens the dashboard at http://localhost:8502 (the worker does not need it).
4. Optional: **`get_prop_rules.bat`** saves the official prop-firm rule pages (config/prop_sources.json) as evidence; then record
   verified rules in Prop Firm Center → Rules & sources → "Record / verify a rule".

Command line (same things): `set PYTHONPATH=src` then `python -m qpl.hub init | status | worker [--once] | jobs | agent-plan |
backup | verify-backup FILE | restore FILE | enqueue KIND | finance-add ... | finance-status ID STATUS | finance-report`.

## What runs by itself (schedules, editable in System Health)
| Job | Every | Does |
|---|---|---|
| ingest | 1 h | new protocols / results / paper ledger hours / data catalogue into the database |
| risk | 1 h | independent risk limits on every paper account (warning / pause / stop; a stop on paper:v98 writes the bot's kill switch) |
| health | 6 h | paper vs backtest z-score, per-sleeve alerts, late hours, stale data |
| backup | 1 day | online SQLite backup + integrity / row-count verification, keeps 14 |
| prop_staleness | 1 day | loads fact files, flags rules unchecked or older than 30 days |
| data_integrity | 1 day | v98 freeze guard (alerts if a baseline file changed) + data catalogue |
| validate_book | 7 days | full validation of the v9.8 book (DSR, Harvey-Liu, bootstrap, stress, acceptance criteria) recorded as an experiment |
| validate_futures | 7 days | the same for the futures book (N = 460 futures trials, trading-day annualisation) |
| agent | 12 h | research agent: next approved agenda item → registered experiment → run → judged by its pre-registered rule |
| daily_summary | 1 day | summary file + notification-centre entry |

Every job is persistent (survives restarts), deduplicated, retried with backoff, time-limited, and visible in System Health.
Notifications: the dashboard's alert list (no external messaging is configured; nothing claims to have sent a message).

## Paper trading in the hub
- **Paper Trading** (dashboard page): create an independent paper account for any Backtest Lab strategy (also your own plug-ins in
  `strategies_user/`) on Binance USDT-M perps, or a portfolio of strategy configurations (netted, with its own costs and a gross cap).
  The worker advances running accounts every 15 minutes; accounts start flat at the next completed bar; pause / resume / stop; a
  reset creates a new account and keeps the old one. Same accounting as the Lab backtest (replay parity 3e-18).
- **Shadow accounts** (Portfolio & Risk): each v9.8 sleeve alone and portfolio variants (e.g. the event-short vol rule, without ridge),
  computed exactly from the running v98 paper trader's ledger. 11 defaults are created automatically; add your own in the form.
- **Composite shadows** (kind `composite`): the v9.8 book PLUS extra sleeves from other paper accounts (e.g. a new strategy running as
  an engine account), combined with the book's own equal-risk rule (`portfolio_v5`, so a 10th sleeve gets 1/10 of the risk once it has
  30 active days). Shows live, before any switch, how "v9.8 + the new sleeve" would have done.
- The v9.8 book itself keeps running in `paper_v98_start.bat` (frozen baseline).

## Futures book
Portfolio & Risk → **Futures book**: equity curve, Sharpe per period, planning Sharpe after the luck haircut, ES/NQ correlation, per-sleeve table
(asset class, leave-one-out) from the F1 audit (`scripts/hub_research/futures_audit.py`). Prop Firm Center → Compatibility → choose the
book (crypto / futures). Paper: `futures_paper_update.bat` once a day (Databento key typed in the window; free cost quote first, downloads only up to the amount you
type), or `futures_paper_once.bat` without downloading. The ledger `paper_trading/futures/ledger_hourly.csv` has one row per CME trading day
and appears in the hub as `paper:futures` (daily health thresholds). Days after 2026-09-30 were never seen by the research.

## CFD paper
`paper_bf26_start.bat` runs the BrightFunded CFD book bf2.6 (crypto CFDs + US100/US500/US30). The hub adds shadow accounts from its ledger:
`bf26:without_carry` (the honest version), `bf26:index_cfds` (index CFDs alone: a possible separate account) and `bf26:crypto_cfds_only`.

## Research agent
`research/hub/agenda.json` holds pre-registered hypotheses (rationale, data needed, whitelisted script, decision rule, priority
inputs). Only `approved` items run; `proposed` items wait for you. The agent never edits strategies, never runs code outside
`scripts/v99/` and `scripts/hub_research/`, and an LLM provider (none configured) could only add `proposed` items.

## Where results are labelled
BACKTEST (research data), PAPER (frozen paper ledger), MODEL ESTIMATE (simulations, income scenarios), ACTUAL (finance ledger).
Payouts count as cash only when marked `received`.

## Files
`src/qpl/hub/` (db, registry, experiments, ingest, metrics, validation, health, risk, prop, prop_snapshots, allocation, finance,
income, jobs, handlers, worker, agent), `app/hub.py`, `config/hub_acceptance.json`, `config/prop_sources.json`,
`research/hub/` (audit and plan, status, agenda, prop fact files), `tests/test_hub.py`.
