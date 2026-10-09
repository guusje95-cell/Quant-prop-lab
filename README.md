# Quant Prop Lab

An autonomous research engine for systematic futures/FX and (since V4) crypto strategies, aimed at
passing prop-firm evaluations legitimately or, where that does not fit, a personal-account paper trial. It covers pinned data, validation, an event-ordered backtester, a
prop-rule simulator, statistics, a permanent experiment database, a paper trader and a report.

**Current status (V4, 2026-10-09): one PAPER-TRADING / PERSONAL-ACCOUNT RESEARCH CANDIDATE, reduced confidence:**
CT1, a BTC daily trend ensemble (TSMOM 20/60/120 + Donchian 20/55, long/short, vol-targeted). It passed pre-registered
TRAIN 1.51, VALIDATION 1.28, OOS 2022-23 0.57 and a single protected-holdout look 2024-01..2026-10 at 0.34 (residual vs
buy & hold 0.30). It also passed on ETH but failed on 21 perps in 2025-26 (-0.02). It is not compatible with the
intraday-only futures prop firms, and the crypto prop rules (all UNCERTAIN) give low pass odds. The other 12 V4 crypto
hypotheses were rejected or left exploratory. No prop-evaluation candidate exists. See `reports/v4_research_report.html`.

**Previous status (v3): NO-GO.** No strategy qualifies as a paper-trading or prop-evaluation
candidate. The v1 candidate (noise-area momentum on Nasdaq futures) failed a pre-registered test on untouched
real ES/YM/RTY futures 2025-26 (pooled Sharpe -0.92) and is EXPLORATORY. See
`reports/v3_research_report.html` and the independent audit `reports/audit_v1_report.html`.
The original v1 report is preserved as `reports/research_report_v1_original.html`.

| | |
|---|---|
| Hypothesis families tested | 22 (0 paper-trading candidates; 2 EXPLORATORY) |
| Unique strategy variants | ~600 (SQLite registry + hash-chained `research_database/ledger.jsonl`) |
| H3 on untouched ES/YM/RTY futures 2025-26 | Sharpe -0.86 / -0.88 / -0.48 |
| Topstep 50K pass probability at 1 MNQ (ESTIMATE) | 75% if 2013-23 edge intact · 28% at 2025-26 edge · 24% no edge |

No result here guarantees profit, an evaluation pass or a payout.

## Commands
```bash
pip install -r requirements.txt
bash scripts/run_tests.sh        # 75 tests (engine, vector engine, prop rules, stats, look-ahead, ledger, clean-room paper parity)
bash scripts/run_v4.sh           # all V4 crypto experiments + reports/v4_research_report.html
python3 scripts/paper_crypto_step.py --bars bars.csv --account spot --start YYYY-MM-DD   # CT1 paper trader (simulation only)
bash scripts/run_v3.sh           # all v3 experiments (re-runs tagged "repro" in the ledger)
bash scripts/run_pipeline.sh     # fetch pinned data + every research generation
bash scripts/reproduce_final.sh  # final candidate analysis + final test
bash scripts/make_report.sh      # v1 report + audit_v1_report.html + v3_research_report.html
```

## Layout
```
config/            data sources (pinned commits), prop-firm rules DB (VERIFIED/UNCERTAIN/NOT_FOUND),
                   final-test protocol (pre-registered), paper-trading config
src/qpl/data       fetch, loaders, validation, sessions/DST, NYSE calendar
src/qpl/features   leakage-safe intraday features (as-of-prior-day mapping)
src/qpl/strategies hypotheses H1-H8 (H9/H10 in experiments/gen6_misc.py)
src/qpl/backtesting numba event-ordered engine, accounting (costs, sizing)
src/qpl/prop_simulation  evaluation rules engine + Monte Carlo
src/qpl/statistics metrics, bootstrap, Newey-West, PSR/DSR, Reality Check/SPA
src/qpl/robustness cost stress, neighbours, regimes, walk-forward, MC
src/qpl/execution  paper trader
src/qpl/research   pipeline, hypothesis docs, experiment registry
experiments/       one script per research generation / evaluation
results/           machine-readable outputs used by the report
```

## Data
The usual vendors are blocked by this environment's network policy. Two public GitHub mirrors
are used, pinned in `config/data_sources.json`: Dukascopy CFD/FX bars for development
(2007/2013 → 2023-09) and TopstepX CME futures bars as the untouched final test
(2025-03 → 2026-04). `data/` is git-ignored; `scripts/run_pipeline.sh` refetches it.
