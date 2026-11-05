"""CN-4 part 2 (protocol research/v99/cn4_protocol.json): bf2.8's netted cost with the BrightFunded TICK spreads (per coin, hour of day,
weekday / weekend; trade window hh:05-15) instead of the 2026-10-21 snapshot. Positions, weights and the netted cost exactly as CN-2
(its code is run unchanged up to the cost step). Writes results/v99/cn4_cost_impact.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/v99/cn2_cfd_netting.py").read_text().split("sv = C.dd(sep - netc)")[0]
g = {"__file__": str(ROOT / "scripts/v99/cn2_cfd_netting.py"), "__name__": "cn2"}; exec(src, g)
C, IX, coins, cost, net, netc, sep, book = (g[k] for k in ("C", "IX", "coins", "cost", "net", "netc", "sep", "book"))
T = pd.read_parquet(ROOT / "results/v99/cn4_spreads.parquet"); T = T[T.window == "hh:05-15"]
normal = {c: v["normal (23-02 excl. 00:00)"] for c, v in json.loads((ROOT / "results/v99/cn4_spread_summary.json").read_text())["per coin"].items()}
hours, wk = IX.hour, IX.weekday >= 5
tick = pd.DataFrame(index=IX, columns=coins, dtype=float); source = {}
for c in coins:
    x = T[T.coin == c]
    if x.empty:
        tick[c] = cost[c]; source[c] = "model (no ticks)"; continue
    lut = {(h, w): v for h, w, v in zip(x.hour, x.weekend, x.bp)}
    nv = normal.get(c, np.nan)
    v = [lut.get((h, w), lut.get((h, not w), nv)) for h, w in zip(hours, wk)]
    tick[c] = (np.array(v, dtype=float) / 2 + g["CB"].COMM) / 1e4; source[c] = "ticks"
turn = g["turn"](net.reindex(columns=coins).fillna(0.0))
tc = (turn * tick).sum(axis=1)
by = pd.DataFrame({"model": (turn * cost).sum().mul(1), "ticks": (turn * tick).sum()})
by = by.div(len(IX) / 8760)                                               # per year, book units
out = {"source per coin": source,
       "annual netted cost, snapshot model (CN-2)": round(float(C.dd(netc).loc["2022":"2026-09-30"].mean() * 365), 4),
       "annual netted cost, tick spreads": round(float(C.dd(tc).loc["2022":"2026-09-30"].mean() * 365), 4),
       "bf2.8 net, snapshot model (CN-2)": C.full(book + (sep - netc)),
       "bf2.8 net, tick spreads": C.full(book + (sep - tc)),
       "share of turnover at 23:00-00:59 UTC": round(float(turn[(hours == 23) | (hours == 0)].sum().sum() / turn.sum().sum()), 3),
       "annual cost by coin (bp of book), model vs ticks": (by * 1e4).round(1).sort_values("ticks", ascending=False).to_dict(orient="index")}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn4_cost_impact.json").write_text(json.dumps(out, indent=1))
