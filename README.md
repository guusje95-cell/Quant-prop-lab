# Quant Prop Lab

An autonomous research engine for systematic futures/FX strategies aimed at passing prop-firm
evaluations legitimately. It covers pinned data, validation, an event-ordered backtester, a
prop-rule simulator, statistics, a permanent experiment database, a paper trader and a report.

**Result:** one conditional candidate, noise-area intraday momentum on Nasdaq-100 futures
(MNQ). See `reports/research_report.html` for the full dossier and strategy card.

| | |
|---|---|
| Hypothesis families tested | 10 (1 survivor) |
| Valid recorded experiments | ~970 (`research_database/experiments.sqlite`) |
| Out-of-sample 2021–23 (1 NQ, after costs) | Sharpe 1.48, NW p = 0.001 |
| Final test, real CME futures 2025-03 → 2026-04 | Sharpe 0.13 (narrow pass; weak) |
| Topstep 50K pass probability (ESTIMATE) | ~76% full edge · ~52% half edge · ~29% 2025-26 regime |

Next step: paper trade first (see `paper_trading/README.md`). No result here guarantees
profit, an evaluation pass or a payout.

## Commands
```bash
pip install -r requirements.txt
bash scripts/run_tests.sh        # 40 tests (engine, prop rules, stats, look-ahead, paper parity)
bash scripts/run_pipeline.sh     # fetch pinned data + every research generation
bash scripts/reproduce_final.sh  # final candidate analysis + final test
bash scripts/make_report.sh      # reports/research_report.html
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
