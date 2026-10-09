"""Step the CT1 crypto paper trader with NEW completed daily bars (simulation only; never sends orders).

Usage:
  python scripts/paper_crypto_step.py --bars bars.csv --account perp|spot [--funding funding.csv] [--state paper_trading/crypto_state_perp.json]
bars.csv:    ts,open,high,low,close  (UTC daily bar OPEN time; only COMPLETED bars)
funding.csv: ts,rate[,mark]          (perp only; settlement time UTC)
The first run needs >= 130 bars of history: bars before --start are used as warm-up (no orders).
State (checkpoint) is written atomically after every run; re-running with the same bars is a no-op (guard rejects old bars).
Data must come from a source you are licensed to use; this tool does not download anything.
"""
import argparse, json, os, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.execution import paper_crypto as P

ap = argparse.ArgumentParser()
ap.add_argument("--bars", required=True); ap.add_argument("--account", choices=("perp", "spot"), required=True)
ap.add_argument("--funding"); ap.add_argument("--state"); ap.add_argument("--start", help="first paper day (UTC date); default: first new bar")
a = ap.parse_args()
state = Path(a.state or f"paper_trading/crypto_state_{a.account}.json"); state.parent.mkdir(parents=True, exist_ok=True)
log = state.with_suffix(".log.jsonl")
bars = pd.read_csv(a.bars, parse_dates=["ts"]).set_index("ts").sort_index()
bars.index = pd.DatetimeIndex(bars.index).tz_localize("UTC") if bars.index.tz is None else bars.index.tz_convert("UTC")
if state.exists():
    r = P.CryptoPaperRunner.restore(json.loads(state.read_text()), log_path=log)
    start = None
else:
    r = P.CryptoPaperRunner(P.PerpAccount() if a.account == "perp" else P.SpotAccount(), log_path=log)
    start = pd.Timestamp(a.start, tz="UTC") if a.start else bars.index[-1]
if a.funding and a.account == "perp":
    f = pd.read_csv(a.funding, parse_dates=["ts"])
    for row in f.itertuples():
        ts = pd.Timestamp(row.ts); ts = ts.tz_localize("UTC") if ts.tz is None else ts
        if r.guard.last is None or ts > r.guard.last:
            r.add_funding(ts, float(row.rate), float(getattr(row, "mark", 0)) or None)
n = 0
for row in bars.itertuples():
    if r.guard.last is not None and row.Index <= r.guard.last:
        continue
    if start is not None and row.Index < start:
        r.warmup(row.Index, row.open, row.high, row.low, row.close)
    else:
        r.on_bar(row.Index, row.open, row.high, row.low, row.close); n += 1
tmp = state.with_suffix(".tmp"); tmp.write_text(json.dumps(r.checkpoint(), default=str)); os.replace(tmp, state)
last = r.history[-1] if r.history else {}
print(json.dumps({"new_paper_bars": n, "equity": last.get("equity"), "next_target_weight": r.pending_w, "killed": r.risk.killed,
                  "guard_events": r.guard.events[-5:]}, default=str, indent=1))
