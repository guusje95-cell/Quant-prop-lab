"""Gen196 (config/gen196_protocol.json): ridge ML sleeve in bf + merged index sleeve. Writes results/gen196.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g)
CS, HB0, per, sh, IDXbf, CB, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "CB", "sleeve"))
k = {"__file__": str(ROOT / "scripts/gen147_cfd_r1.py")}; exec(open(ROOT / "scripts/gen147_cfd_r1.py").read().split("P6 = p6()")[0], k)
IDXS = k["P6"] if "P6" in k else None
P6 = k["p6"](); R1 = k["r1"](1e-4)
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet"); wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
hb = sleeve(CB.d2h(wml.reindex(columns=CB.CFD).fillna(0.0), IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))))
IS = (P6 + R1).rename("vol-managed indices")
ref = CS.portfolio_v5(pd.concat([HB0, IS], axis=1).fillna(0.0))[0]; B0, k0 = sh(ref, "2022-01-01", "2026-09-30"), per(ref, "2022-01-01")
vb = CS.portfolio_v5(pd.concat([HB0, IS, hb.rename("ridge ML")], axis=1).fillna(0.0))[0]; B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
p = per(hb, "2020-01-01")
out = {"reference": [round(B0, 3), np.round(k0, 3).tolist()], "ridge sleeve D/T/H (CFD costs)": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen196.json", "w"), indent=1)
if out["pass"]:
    vb.to_frame("book").to_parquet(ROOT / "results/gen196_book.parquet")
