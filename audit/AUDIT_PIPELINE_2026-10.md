# Pipeline audit: calendars, NaNs, gaps, timing, rolls (V6 futures pipeline)
Scope: `src/qpl/data/futures_panel.py`, `src/qpl/backtesting/panel.py`, `src/qpl/strategies/futures_factors.py`, `src/qpl/strategies/f9.py`.
All scripts are read-only diagnostics; no strategy, data or parameter was changed.

| # | Finding | Class | Evidence (reproduce) |
|---|---|---|---|
| A1a | `load_instrument` groups by calendar date (`groupby(date).last()`). Sunday-evening Globex reopening prints (22:00–23:45) therefore become separate "Sunday" rows: 16,516 obs in 86 instruments, 2009–2024 (hourly era). | Possible risk → impact-tested, **not material to the conclusions** | `audit/a1_calendar_gaps.py`; `audit/a2_weekend_impact.py` |
| A2 | Impact of removing weekend prints: F7 1.51/0.63/0.96/0.70 → 1.51/0.80/1.01/0.66; F9 1.60/0.91/1.21/0.73 → 1.60/1.04/1.30/0.79 (DISC/VAL/TEST/HOLDOUT). Production is mostly *conservative*; the convention moves Sharpe by up to ±0.17. | Uncertainty band, not a bug | `audit/a2_weekend_impact.py` |
| A1b | Returns across missing trading days are booked as one return on the next observation (3% of obs, 4.7% of return variance on median; multi-day abs return ≈ 1.26× single-day). P&L is correct (the position is held over the gap). Vol estimation treats them as one-day returns → slight **upward** vol bias (conservative sizing). V6 sigma vs a pysystemtrade-style business-day sigma: median ratio 1.00 (p1 0.83, p99 1.31). | Appears correct; minor | `audit/a1_calendar_gaps.py` |
| A1c | Union calendar: 12.7% of cells after an instrument's start are NaN (other markets' holidays, Sundays). Engine fills NaN returns with 0 for P&L; signals use a forward-filled log index; lookbacks are counted in union rows, not the instrument's own trading days (≈ 13% shorter effective lookback). | Definitional deviation, not look-ahead | `audit/a1_calendar_gaps.py` |
| A3 | Timing canary on real data (TSMOM, 2005–2024): lag 0 (cheating, earns the decision-day return) Sharpe **5.96**; lag 1 0.74; lag 2 (production) 0.67. Leakage would be visible; production is causal. Unit tests for signal look-ahead and the 2-row lag pass (13/13). | Correct | `audit/a3_timing_roll.py`; `pytest tests/test_futures_panel.py tests/test_paper_futures.py` |
| A4 | Roll days: `ret = dADJ / PRICE_{t-1}` uses the old contract's price instead of the new one (`FORWARD_{t-1}`). Median error 0.1–3 bp per roll day; total error < 0.03% of absolute returns on 8 instruments. | Proven deviation, **immaterial** | `audit/a3_timing_roll.py` |
| — | Duplicates: removed by per-date grouping; 0 duplicate index entries. | Correct | `audit/a1_calendar_gaps.py` |
| — | Costs: turnover × cost, booked on the trade row; unit test passes. | Correct within the cost model | `tests/test_futures_panel.py::test_costs_charged_on_turnover` |

## Remaining uncertainties (not investigated further: no concrete sign of a material problem)
1. Universe filters use full-sample cost/vol/staleness statistics (mild look-ahead in *selection*, not in signals).
2. Bad-tick repair (`drop_spikes`) uses t+1.
3. The `SpreadCost` table is used as-is; whether it is a half or full spread is not verified against pysystemtrade docs.
4. Timestamps are taken as published (they appear to be UK time); daily "close" = last print of the calendar date, which in the hourly era is an evening Globex print, not the settlement.
5. pysystemtrade's own `resample("1B").last()` puts Sunday-evening prints in Friday's bin (Friday value contains Sunday information). That is a property of the external library; our pipeline does not use it, but any reconciliation against pysystemtrade output must account for it.
