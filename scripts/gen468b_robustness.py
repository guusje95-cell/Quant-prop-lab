"""Gen468b (descriptive robustness for the flagged Gen468 event short v2). Writes results/gen468b.json."""
import json
import runpy
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
ARCH = ROOT / "data/lab/binance_vision"
G = runpy.run_path(str(ROOT / "scripts/gen467_event_shorts.py"), run_name="gen467_lib")
idx, EVL, PL, CFL, CS, unit, shp, per, V7, REF, EV = (G[k] for k in ("idx", "EVL", "PL", "CFL", "CS", "unit", "shp", "per", "V7", "REF", "EV"))
Lr = {}
for s, t0, c, f in EVL:
    e = (t0 + pd.Timedelta(hours=24)).ceil("D"); m = ARCH / f"{s}_metrics.parquet"
    if m.exists():
        x = pd.read_parquet(m, columns=["time", "count_long_short_ratio"]); x["time"] = pd.to_datetime(x["time"])
        v = x[(x["time"] >= e - pd.Timedelta(hours=24)) & (x["time"] < e)]["count_long_short_ratio"].astype(float).dropna()
        if len(v) > 50:
            Lr[s[:-4]] = float(v.mean())
def run(piv=1.5, lo=0.5, hi=2.0, hold=14, cost=10.0, lag=0, cap=0.5, deli=True):
    PLs = PL.copy()
    for n in PLs.columns:
        PLs[n] = PLs[n] * (float(np.clip(Lr[n] / piv, lo, hi)) if n in Lr else 1.0)
    parts, CF = [PLs], dict(CFL)
    if deli:
        P2, CF2, _ = G["positions"](EV["spot delisting"], hold); parts.append(P2.add_prefix("spo_")); CF.update({"spo_" + c: v for c, v in CF2.items()})
    P = pd.concat(parts, axis=1).reindex(idx).fillna(0.0).shift(lag).fillna(0.0)
    g = P.abs().sum(axis=1); P = P.mul((cap / g).clip(upper=1.0).fillna(1.0), axis=0)
    s_ = pd.Series(0.0, index=idx)
    for n in P.columns:
        c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * cost / 1e4
    b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_}))[0])
    return {"sleeve": per(s_), "book": [shp(b), per(b)]}
cases = {"base (Gen468)": {}, "costs x2": {"cost": 20.0}, "1 h later": {"lag": 1}, "6 h later": {"lag": 6},
         "pivot 1.2": {"piv": 1.2}, "pivot 2.0": {"piv": 2.0}, "clip 0.75-1.5": {"lo": 0.75, "hi": 1.5}, "clip 0.25-3": {"lo": 0.25, "hi": 3.0},
         "delisting hold 7": {"hold": 7}, "delisting hold 30": {"hold": 30}, "cap 0.35": {"cap": 0.35}, "cap 0.75": {"cap": 0.75},
         "crowding only (Gen461)": {"deli": False}}
out = {"reference v9.7": [REF[0], REF[1]]}
for k, kw in cases.items():
    out[k] = run(**kw); print(k, out[k], flush=True)
(ROOT / "results/gen468b.json").write_text(json.dumps(out, indent=1))
