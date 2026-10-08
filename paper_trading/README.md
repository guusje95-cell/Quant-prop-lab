# Paper trading — H3 noise-area momentum (MNQ)

Paper only. Nothing here sends orders to a broker. Real-money or live-evaluation use needs your
explicit decision and a separately reviewed execution adapter.

## Run
```bash
# replay real futures history (sanity check; reproduces the backtest exactly)
python paper_trading/run_paper.py --replay data/processed/topstepx/MNQ_15min.parquet
# your own bars: CSV with datetime (UTC, bar OPEN time), open, high, low, close, volume
python paper_trading/run_paper.py --csv my_mnq_15m.csv
```
Live: call `PaperTrader.on_bar(ts, o, h, l, c, v)` from your market-data callback each time a
15-minute bar completes. Config: `config/paper_trading.json` (Topstep 50K rules, 1 MNQ sizing).

## Output
`paper_trading/logs/*.jsonl`: one line per signal, fill, trade, rule event, day and monitor
update, with the bar timestamp and wall-clock time. `last_trades.csv` / `last_days.csv` are summaries.

## Go / no-go gate (pre-registered)
Minimum 60 trading days (~50 trades) at 1 MNQ.
* GO (buy one Topstep 50K Combine): cumulative P&L per contract > 0 and monitor z > -1.0, with
  live fills within ~1 tick of simulated prices.
* EXTEND to 100 trades: -2 <= z <= -1.
* STOP: z < -2 after >= 30 trades (the kill switch logs `KILL_SWITCH`). Do not buy evaluations.

Expectation per trade (1 MNQ, 2013-2023 backtest): +$27.6 mean, $243 sd; ~2.3 trades/week.
