"""Gen127 P6 (config/gen127_protocol.json): vol-managed US100/US500 CFDs as a 7th sleeve of the bf book (swap-free).
Weight 0.5 x 0.15 / 20-day vol (cap 2x) per index, decided at the previous UTC day, 1 bp per side. Writes results/gen127_p6.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g)
CS, HB0, bb0, kb0, BB0, per, sh, IDXbf = (g[k] for k in ("CS", "HB0", "bb0", "kb0", "BB0", "per", "sh", "IDXbf"))
DUK = ROOT / "research_data/dukascopy"; legs = []
for s in ("US100", "US500"):
    x = pd.read_parquet(DUK / f"{s}_1h.parquet")["close"].astype("float64"); x = x[~x.index.duplicated()].sort_index()
    x = x.reindex(IDXbf).ffill(limit=72)
    r = x.pct_change().fillna(0.0)
    dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
    w = (0.5 * (0.15 / vol).clip(upper=2.0)).shift(1)                       # decided with days before d
    wh = w.reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
    legs.append(wh * r - wh.diff().abs().fillna(0.0) * 1e-4)
p6 = sum(legs)
vb = CS.portfolio_v5(pd.concat([HB0, p6.rename("vol-managed indices")], axis=1).fillna(0.0))[0]; kb1 = per(vb, "2022-01-01")
out = {"sleeve 2022-26 Sharpe": round(sh(p6, "2022-01-01", "2026-09-30"), 3), "sleeve D/T/H (2020-22/23-24/25-26)": np.round(per(p6, "2020-01-01"), 3).tolist(),
       "bf before": [round(BB0, 3), np.round(kb0, 3).tolist()], "bf after": [round(sh(vb, "2022-01-01", "2026-09-30"), 3), np.round(kb1, 3).tolist()]}
out["pass (strict bf rule)"] = bool(out["bf after"][0] > BB0 and kb1[1] >= kb0[1] and kb1[2] >= kb0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen127_p6.json", "w"), indent=1)
