# Quant Prop Lab

An autonomous research engine for systematic futures/FX strategies aimed at passing prop-firm
evaluations legitimately. It covers pinned data, validation, an event-ordered backtester, a
prop-rule simulator, statistics, a permanent experiment database, a paper trader and a report.

**Current status (v3, 2026-10-09): NO-GO.** No strategy qualifies as a paper-trading or prop-evaluation
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
bash scripts/run_tests.sh        # 59 tests (engine, prop rules, stats, look-ahead, ledger, clean-room paper parity)
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
