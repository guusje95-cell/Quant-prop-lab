"""WE-1 (protocol research/v99/we1_protocol.json): Weiss entry at 07:57 UTC vs the frozen 08:00 entry, per trade, unseen 2020-21 +
2026-10-30 and all days. Writes results/v99/we1_weiss_early.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "research_data/binance_1m_weiss"
days = pd.date_range("2020-01-03", "2026-10-31", freq="W-FRI"); days = days[(days + pd.Timedelta(days=7)).month != days.month]
rows = []
for d in days:
    for sym in ("BTCUSDT", "ETHUSDT"):
        f = CACHE / f"{sym}_{d.date()}.parquet"
        if not f.exists():
            continue
        o = pd.read_parquet(f)["open"]; t7, t8, t10 = d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=10)
        if not all(t in o.index for t in (t7, t8, t10)):
            continue
        r = {"day": d, "coin": sym[:3]}
        for k in (-5, -3, -2, -1, 0):
            te = t8 + pd.Timedelta(minutes=k)
            if te not in o.index or o[te] == o[t7]:
                r[k] = np.nan; continue
            r[k] = (-np.sign(o[te] / o[t7] - 1) * (o[t10] / o[te] - 1) - 0.001) * 1e4
        rows.append(r)
T = pd.DataFrame(rows).dropna(); T["unseen"] = (T.day < "2022-01-01") | (T.day > "2026-09-30")
t = lambda x: round(float(x.mean() / x.std() * np.sqrt(len(x))), 2)
def block(X):
    return {"trades": len(X), "days": int(X.day.nunique()), "mean bp by entry": {f"{k:+d} min": round(float(X[k].mean()), 1) for k in (-5, -3, -2, -1, 0)},
            "t by entry": {f"{k:+d} min": t(X[k]) for k in (-5, -3, -2, -1, 0)},
            "paired 07:57 minus 08:00: mean bp / t": [round(float((X[-3] - X[0]).mean()), 1), t(X[-3] - X[0])]}
out = {"unseen (2020-21 + 2026-10-30)": block(T[T.unseen]), "seen (2022-01..2026-09)": block(T[~T.unseen]), "all": block(T),
       "by year: 07:57 / 08:00 mean bp": {str(y): [round(float(g[-3].mean()), 1), round(float(g[0].mean()), 1), len(g)] for y, g in T.groupby(T.day.dt.year)}}
u = out["unseen (2020-21 + 2026-10-30)"]; a = out["all"]
out["verdict"] = "PASS" if (u["paired 07:57 minus 08:00: mean bp / t"][0] > 0 and u["mean bp by entry"]["-3 min"] > 0 and a["paired 07:57 minus 08:00: mean bp / t"][1] >= 2) else "FAIL"
print(json.dumps(out, indent=1, default=str)); (ROOT / "results/v99/we1_weiss_early.json").write_text(json.dumps(out, indent=1, default=str))
