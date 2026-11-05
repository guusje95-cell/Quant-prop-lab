"""CN-4 part 1 (protocol research/v99/cn4_protocol.json): BrightFunded MT5 tick spreads per coin / hour (UTC), trade window hh:05-hh:15.
Writes results/v99/cn4_spreads.parquet (coin, hour, weekend, window -> median bp) and prints a summary vs the 2026-10-21 snapshot."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "research_data/firm_ticks/BrightFunded_Ltd"
WIN = {"hh:05-15": (5, 15), "hh:15-25": (15, 25), "hh:30-40": (30, 40)}


def coin(f):
    s = f.name.rsplit("_", 1)[0]
    return {"XDGUSD": "DOGE"}.get(s, s.replace("USD", "") if s.endswith("USD") else s.replace("_cash", ""))


rows, normal = [], {}
for f in sorted(D.glob("*.parquet")):
    c = coin(f); x = pd.read_parquet(f)
    x = x[(x.ask > x.bid) & (x.bid > 0)]
    if x.empty:
        continue
    t = pd.DatetimeIndex(x.time); bp = ((x.ask - x.bid) / ((x.ask + x.bid) / 2) * 1e4).to_numpy()
    s = pd.Series(bp, index=t)
    m = t.minute
    for w, (a, b) in WIN.items():
        k = (m >= a) & (m < b)
        g = s[k].groupby(s[k].index.floor("h")).median()
        rows += [{"coin": c, "hour_ts": h, "window": w, "bp": v} for h, v in g.items()]
    nm = ~(((t.hour == 23) & (m >= 55)) | ((t.hour == 0) & (m < 15)))
    normal.setdefault(c, []).append(float(np.median(bp[nm])) if nm.any() else np.nan)
R = pd.DataFrame(rows); R["hour"] = R.hour_ts.dt.hour; R["weekend"] = R.hour_ts.dt.weekday >= 5
T = R.groupby(["coin", "window", "hour", "weekend"]).bp.median().rename("bp").reset_index()
T.to_parquet(ROOT / "results/v99/cn4_spreads.parquet")
N = pd.Series({c: float(np.nanmedian(v)) for c, v in normal.items()}, name="normal")
spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[0])
snap = pd.Series({s.split("/")[0].replace("XDG", "DOGE").replace(".cash", ""): v for s, v in zip(spec.symbol, spec.spread_bp_median)})
w5 = T[T.window == "hh:05-15"]
summ = pd.DataFrame({"snapshot 10-21": snap.reindex(N.index), "normal (23-02 excl. 00:00)": N,
                     "00:05-15 weekday": w5[(w5.hour == 0) & ~w5.weekend].set_index("coin").bp,
                     "00:05-15 weekend": w5[(w5.hour == 0) & w5.weekend].set_index("coin").bp,
                     "01:05-15 weekday": w5[(w5.hour == 1) & ~w5.weekend].set_index("coin").bp}).round(2)
print(summ.to_string())
for c in ("BTC", "ETH"):
    p = w5[(w5.coin == c) & ~w5.weekend].set_index("hour").bp; q = w5[(w5.coin == c) & w5.weekend].set_index("hour").bp
    print(c, "weekday by hour:", p.round(2).to_dict()); print(c, "weekend by hour:", q.round(2).to_dict())
(ROOT / "results/v99/cn4_spread_summary.json").write_text(json.dumps({"per coin": summ.to_dict(orient="index"),
    "BTC/ETH by hour (hh:05-15, weekday / weekend)": {c: {"weekday": w5[(w5.coin == c) & ~w5.weekend].set_index("hour").bp.round(3).to_dict(),
                                                          "weekend": w5[(w5.coin == c) & w5.weekend].set_index("hour").bp.round(3).to_dict()} for c in ("BTC", "ETH")}}, indent=1, default=str))
