# Quant Trading Hub: implementation status (kept current; resume from here after a restart)

Updated 2026-10-30. Evidence = tests in `tests/test_hub.py` (25 passing; full suite: see the bottom line), and an end-to-end run on the real
project data in the cloud workspace (init, one worker pass, every dashboard page and its computation buttons).

| # | Subsystem | Status | Evidence / limits |
|---|---|---|---|
| 1 | Core data model, migrations, audit, settings, backups | Implemented and tested | 2 versioned migrations (checksum-protected), WAL, transactional writes, audit rows; backup + integrity / row-count verification + restore tested |
| 2 | Strategy registry + immutable versions + lifecycle | Implemented and tested | DB trigger blocks edits; same config = same version; transitions need reasons, approvals need a scope; 9 v9.8 sleeves + futures and CFD books registered |
| 3 | Experiment registry | Implemented and tested | 2,454 legacy variants + 462 protocols (2 unparseable, recorded) ingested idempotently; holdout use flagged; results final; trial counts |
| 4 | Autonomous research orchestration | Implemented, partially tested | agenda → register → run (whitelisted, timeout, no credentials) → pre-registered decision; first real run done (event-short vol regime). LLM provider interface only (none configured) |
| 5 | Strategy discovery / common backtester | Partially implemented | the project's existing engines are reused (`qpl.lab.engine`, sleeve scripts); no new generic multi-market backtester was built |
| 6 | Robustness / statistical validation | Implemented and tested | periods, non-normal SE, block bootstrap, project haircut, DSR, Harvey-Liu, CSCV-PBO, stress proxies, acceptance criteria per use case |
| 7 | Paper trading | Implemented and tested; live data path untested here | (a) ingests the existing paper traders' frozen ledgers (v98 stays in `scripts/paper_v5.py`, frozen); (b) **shadow accounts** per sleeve / reweighted / custom / rule, derived exactly from the paper ledger (neutral shadow = source to 1e-15); (c) **hub paper engine**: independent accounts for any Lab strategy or a portfolio of strategies, bar by bar, backtest parity 3e-18 (replay test), idempotent, restart-safe, pause / stop / reset-as-new-account, fail-closed on stale data. The live Binance USDT-M data provider cannot be reached from the cloud, so it is exercised only on the PC |
| 8 | Portfolio construction | Implemented, partially tested | portfolio versions (immutable), risk contributions, correlation, stress cases; allocation research results in research/v99 (R3 rejected). Futures book registered as portfolio `futures_book` gen238 (15 sleeves, state validation) with its own dashboard tab (backtest, F1 audit numbers) and a weekly `validate_futures` job (N = 460, 252-day annualisation) |
| 9 | Independent risk management | Implemented and tested | limits table, hysteresis, events, alerts, bot kill switch for v98; reads paper equity only (no live accounts exist) |
| 10 | Strategy health | Implemented, partially tested | z-score vs backtest with minimum samples, per-sleeve alert levels, late hours, staleness; diagnostics, never retunes |
| 11 | Prop-firm rules database | Implemented and tested, data not verified | versioned rule sets + per-field facts with source / date / quote / status; 0 facts verified: the firms' sites are blocked from the cloud; `get_prop_rules.bat` + dashboard verification form |
| 12 | Compatibility engine | Implemented and tested | verified / potentially / incompatible / insufficient; unverified facts can never yield "verified compatible". Profiles: crypto v9.8 and futures book; firm-wide policy facts (e.g. 'flat at the close') apply to every account type of that firm. Futures firms MFFU / Tradeify / Topstep / Apex recorded as not allowing overnight holding (uncertain, from project notes), PropShop Trader as a swing + bot candidate (assumption) |
| 13 | Challenge + funded simulator | Implemented, partially tested | rule engine `qpl.lab.propfirms` on rule-set parameters, results stored with the rule-set version; model estimates only |
| 14 | Multi-account allocation | Implemented, smoke-tested | enumerates plans under account / fee / concentration constraints; shared return path; conservative vs aggressive rankings |
| 15 | Finance ledger | Implemented and tested | statuses planned → requested → approved → received; history; only received counts as cash; FX never guessed |
| 16 | Income planner | Implemented and tested | per-account cash simulation at an assumed live Sharpe, rejection / delay / costs / FX / tax placeholder; P(month ≥ target) |
| 17 | Dashboard | Implemented and tested | 8 views on real data; empty-database render test; labels BACKTEST / PAPER / MODEL / ACTUAL |
| 18 | Scheduling, jobs, worker | Implemented and tested | persistent queue, dedup, retries + backoff, timeouts, heartbeats, stale recovery, child processes, CPU budget, graceful stop, Windows task |
| 19 | Security boundaries | Implemented and tested | live trading locked off, no live adapter, script whitelist, credentials stripped from research job environments |
| 20 | Notifications | Partially implemented | internal notification centre (alerts) only; no external channel configured |

## Known limitations / next steps
1. Prop rules: verify HyroTrader / CFT / Breakout facts from official pages (run `get_prop_rules.bat`, then record quotes). Until then every
   compatibility result is at best "potentially compatible".
2. Paper engine: first live run on the PC still to be observed (the Binance data provider is untested from the cloud). The v9.8 sleeves themselves are not Lab plug-ins: per-sleeve views come from shadow accounts, not from the engine.
3. Futures book: backtest + validation + compatibility in the hub, and a **futures paper trader** (`futures_paper_update.bat`: capped Databento top-up after a free cost quote, then `scripts/futures_paper.py` appends each completed CME day once; exact rebuild check 1e-17, simulated incremental path 1e-16; the hub ingests `paper_trading/futures` as a daily ledger). Not yet run on the PC. CFD: the bf2.6 paper trader (`paper_bf26_start.bat`, still computes on the research pack) ran 4 days in October; the hub derives shadows `bf26:without_carry`, `bf26:index_cfds`, `bf26:crypto_cfds_only` from it.
4. The research agent has one runnable approved item; the Bybit item waits for `get_bybit_announcements.bat`.
6. R1 limit-order study: Bybit tick re-measurement (`scripts/v99/r1b_ticks.py`) and a read-only order-book logger (`book_logger_start.bat`, 23:59-00:12 UTC, public data) for a queue-aware fill model; the logger is untested from the cloud (Bybit answers 403 here).
5. External notifications (e-mail / Telegram) not configured: needs the user's choice and credentials (would go in a secret store, not in code).

Dashboard fix 2026-10-30: one SQLite connection per Streamlit thread (a rerun on another thread raised 'SQLite objects created in a thread ...').

Full test suite on 2026-10-30 after the futures integration: **199 passed**, 0 failed (`python -m pytest tests`).
