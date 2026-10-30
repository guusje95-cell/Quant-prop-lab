# Quant Trading Hub: project audit and implementation plan

Written 2026-10-30, before any hub code. Evidence = files in this repository and commands run in this session.

## 1. What exists (audit)

| Area | What is there | State |
|---|---|---|
| Language / stack | Python 3.11+ (3.13 here), pandas / numpy / scipy / numba, pytest; Streamlit + Plotly app (`app/lab.py`); Windows `.bat` launchers on the user's PC; git as the transport between this cloud workspace and the PC | working |
| Tests | 19 files in `tests/`; **174 passed, 0 failed** (2026-10-30 baseline, 124 s) | working |
| Market data | `research_data/` 2.6 GB in git (Binance pack 5-min for 20 coins, 40 extra coins hourly, point-in-time archive incl. delisted perps, Upbit, Coinbase, Bybit / OKX listings, announcements, Deribit, Hyperliquid); `data/` 11 GB local cache (Binance vision, futures panel, Dukascopy CFDs). Validation helpers in `src/qpl/data/validate.py` | working, no central catalogue or freshness view |
| Strategies | Crypto sleeves in `scripts/crypto_sleeves.py`, `basket_live.py`, `event_live.py`, `ridge_live.py`, `alt_kimchi.py`; futures book scripts (Gen135-238); CFD book `scripts/cfd_book.py`; Lab plug-ins `src/qpl/lab/strategies*.py`, `strategies_user/` | working; strategies are code + config, not versioned objects |
| Experiments | Legacy SQLite registry `research_database/experiments.sqlite` (2,454 rows, up to Gen25, 2026-10-09) + hash-chained `ledger.jsonl` (640 rows); since then 424 pre-registered protocols `config/gen*_protocol.json` (sum of `trials_added` = 1,849), results `results/gen*.json`, narrative `research/LEADERBOARD.md` (201 sections), v9.9 log `research/v99/` | **fragmented**: three record systems, the newest is prose |
| Validation | Deflated Sharpe, bootstrap, walk-forward, CSCV/PBO, Harvey-Liu exist as one-off scripts (`gen325`, `v99/a1_methodology.py`) and in the Lab (`src/qpl/lab/analysis.py`) | working but not a reusable pipeline |
| Paper trading | `scripts/paper_v5.py` (hour-by-hour, frozen ledger, self-test, reconcile) for books v5 ... v98 and bf / bf2 ... bf26; output CSV / JSONL under `paper_trading/<ver>/` on the user's PC; `scripts/paper_report.py` (z-score gate, per-sleeve alerts); live baseline **v98 frozen** (`config/v98_freeze.json`, guard `scripts/v99/check_v98_freeze.py`) | working; one account per book version; results reach this repo only when the user runs `*_share.bat` |
| Execution / bot | `src/qpl/bot/` dry-run runner (rules, planner, guard, kill switch `bot_state/STOP`, adapters = dry-run only) | working, dry-run only |
| Prop firms | `src/qpl/lab/propfirms.py` (rule-based challenge + funded simulator, presets), `config/prop_firms*.json` (rules marked VERIFIED / UNCERTAIN / NOT_FOUND with notes; 2026-10-09: official sites were not reachable then, so nothing VERIFIED), `research/FIRM_RULES_EXECUTION.md` | simulator working; rules not sourced per field, not versioned |
| Portfolio / risk | `CS.portfolio_v5` (equal risk, vol targeting), bot guard, paper daily stop | working inside the paper code; no independent risk service |
| Finance / income | Account-income simulations (Gen325 / 332 / 437 / 452 / 468c / 472c) | one-off scripts; no ledger of real fees / payouts |
| Scheduling | `paper_*_start.bat` loops, `paper_v5_schedule.bat`; nothing else runs unattended | partial |
| Dashboard | `app/lab.py` (Backtest Lab: backtests, honesty checks, prop simulation) | working; no hub views |

Risks found: (1) the newest research exists only as prose plus JSON, so trial counts and decisions are hard to query; (2) paper
results live on the user's PC and arrive only via git; (3) prop rules are unsourced snapshots; (4) no backup/restore of research
state beyond git; (5) no unattended research loop; (6) live trading is impossible today (good) and must stay so by default.

## 2. Architecture decision
One Python package `src/qpl/hub/` with a single **SQLite** database (`hub_data/hub.sqlite`, WAL mode, versioned SQL migrations,
not in git; it is rebuilt or backed up locally). Reasons: the workload is one user on one PC, SQLite is transactional and needs no
server, everything else in the project is already file-based. Git stays the transport for research artifacts; the hub INGESTS
them idempotently (legacy registry, protocols, results, paper ledgers, v9.9 log). The frozen v98 paper trader is not modified: the
hub reads its outputs.

Logical subsystems -> modules: `db` (connection, migrations, audit, settings, backups), `registry` (strategies, immutable versions,
lifecycle), `experiments` (hypotheses, experiments, trial counting, dedup by config hash), `ingest`, `metrics` + `validation`
(standard metrics, DSR, PBO-CSCV, Harvey-Liu, block bootstrap, stress, acceptance criteria per use case), `paper` (paper accounts
from the paper ledgers, equity / fills, backtest-vs-paper deviation), `health`, `risk` (independent rules -> actions incl. the bot
kill switch), `prop` (firms, sourced rule facts, versioned rule sets, compatibility, challenge simulation via `propfirms.py`,
multi-account allocation), `finance` (cash ledger with payout states), `income` (scenario Monte Carlo), `jobs` + `worker` (persistent
queue, dedup, retries with backoff, timeouts, heartbeats, recovery, budgets, scheduler), `agent` (research agenda, prioritisation,
whitelisted experiment templates, out-of-sample tracking of every registered sleeve; LLM provider interface off by default),
`app/hub.py` (Streamlit dashboard). CLI: `python -m qpl.hub ...`. Launchers: `hub_start.bat`, `hub_dashboard.bat`.

Safety: `settings.live_trading_enabled` is fixed false; there is no live adapter; the worker only runs whitelisted job kinds and
scripts; no job can spend money, place orders or touch credentials.

## 3. Plan (vertical slices, each tested)
1. Core: db + migrations + audit + settings + backup/verify-restore; registry with immutable versions and lifecycle; experiments.
2. Ingestion of all existing records; standard metrics and validation pipeline; acceptance criteria file.
3. Paper accounts from the paper ledgers (v86, bf26 present in the repo; v98 when shared); health checks; backtest-vs-paper.
4. Independent risk manager; portfolio versions (v9.8 sleeve weights) with risk contributions and stress tests.
5. Prop firm database (firms, rule facts with source / date / quote / confidence, versioned rule sets), compatibility engine,
   challenge simulator on rule sets, multi-account allocation.
6. Finance ledger (fees, payout requested / approved / received, reserves) and income scenario engine (conservative / base /
   optimistic, nothing counted as cash before it is received).
7. Jobs worker + scheduler + research agent with budgets; daily summary into the notification centre.
8. Dashboard (Overview, Research Lab, Strategy Center, Portfolio & Risk, Prop Firms, Income Planner, Finance, System Health),
   acceptance tests, docs (`research/hub/STATUS.md` kept current).
