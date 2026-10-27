"""Gen468 (config/gen468_protocol.json, FLAGGED post hoc): Gen461 crowding-sized listing short + Gen467 A spot-delisting shorts.
Writes results/gen468.json."""
import json
import runpy
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
ARCH = ROOT / "data/lab/binance_vision"
G = runpy.run_path(str(ROOT / "scripts/gen467_event_shorts.py"), run_name="gen467_lib")   # re-runs Gen467 (same output) and exposes its helpers
idx, EVL, PL, CFL, CS, unit, shp, per, V7, REF = (G[k] for k in ("idx", "EVL", "PL", "CFL", "CS", "unit", "shp", "per", "V7", "REF"))
size = {}
for s, t0, c, f in EVL:
    e = (t0 + pd.Timedelta(hours=24)).ceil("D"); m = ARCH / f"{s}_metrics.parquet"; k = 1.0
    if m.exists():
        x = pd.read_parquet(m, columns=["time", "count_long_short_ratio"]); x["time"] = pd.to_datetime(x["time"])
        v = x[(x["time"] >= e - pd.Timedelta(hours=24)) & (x["time"] < e)]["count_long_short_ratio"].astype(float).dropna()
        if len(v) > 50:
            k = float(np.clip(float(v.mean()) / 1.5, 0.5, 2.0))
    size[s[:-4]] = k
PLs = PL.copy()
for n in PLs.columns:
    PLs[n] = PLs[n] * size.get(n, 1.0)
P2, CF2, n2 = G["positions"](G["EV"]["spot delisting"], 14)
P = pd.concat([PLs, P2.add_prefix("spo_")], axis=1).reindex(idx).fillna(0.0)
CF = dict(CFL); CF.update({"spo_" + c: v for c, v in CF2.items()})
g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
s_ = pd.Series(0.0, index=idx)
for n in P.columns:
    c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_}))[0]); r = [shp(b), per(b)]
yrs = {y: shp(s_, y, y) for y in ("2022", "2023", "2024", "2025", "2026")}
out = {"reference v9.7": [REF[0], REF[1]], "delisting events traded": n2, "sleeve": per(s_), "sleeve by year": yrs, "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen468.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
