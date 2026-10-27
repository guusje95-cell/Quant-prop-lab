"""Gen471 (config/gen471_protocol.json): inverse-vol sizing of each event in the v9.8 event short. Writes results/gen471.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
K = []
def invvol(P, CF):
    P = P.copy()
    for n in P.columns:
        p = P[n]; c = CF[n][0]; nz = (p != 0).astype(int)
        starts = p.index[(nz.diff().fillna(nz) == 1).to_numpy()]
        for i, t1 in enumerate(starts):
            t2 = starts[i + 1] if i + 1 < len(starts) else p.index[-1] + pd.Timedelta(hours=1)
            r = c.loc[t1 - pd.Timedelta(hours=26):t1 - pd.Timedelta(hours=1)].pct_change().dropna().iloc[-24:]
            k = float(np.clip(1.5 / (r.std() * np.sqrt(24 * 365)), 0.5, 2.0)) if len(r) >= 12 and r.std() > 0 else 1.0
            K.append(k); P.loc[t1:t2 - pd.Timedelta(hours=1), n] *= k
    return P
s8, _, _ = EL.pnl(idx); b8 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s8}))[0]); R8 = [shp(b8), per(b8)]
s, _, _ = EL.pnl(idx, pre_cap=invvol); b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.8": R8, "events sized": len(K), "multiplier (median / p10 / p90)": [round(float(np.median(K)), 2), round(float(np.percentile(K, 10)), 2), round(float(np.percentile(K, 90)), 2)],
       "sleeve": per(s), "book": r, "pass": bool(r[0] >= R8[0] + 0.05 and all(r[1][i] >= R8[1][i] for i in range(3)))}
(ROOT / "results/gen471.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
