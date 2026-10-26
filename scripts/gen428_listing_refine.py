"""Gen428 (config/gen428_protocol.json): listing-short refinements. Writes results/gen428.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
EV = LL.events()
FI = {}                                                          # funding interval hours per symbol (from the archive file)
for s, *_ in EV:
    f = LL.PIT / f"{s}_funding.parquet"
    FI[s] = float(pd.read_parquet(f)["funding_interval_hours"].median()) if f.exists() and "funding_interval_hours" in pd.read_parquet(f).columns else 8.0
LL.CAP = 1e9
def sized(EVx, size_fn):
    P = LL.positions(idx, EVx)
    for s, t0, c, f in EVx:
        n = s[:-4]
        if n in P:
            P[n] = P[n] * size_fn(s, t0, c, f)
    g = P.abs().sum(axis=1); return P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
CF = {s[:-4]: (c, f) for s, t0, c, f in EV}
def pnl(P):
    out = pd.Series(0.0, index=idx)
    for n in P.columns:
        c, f = CF[n]; p = P[n]
        r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * LL.COST_BP / 1e4
    return out
entry = lambda t0: (t0 + pd.Timedelta(hours=24)).ceil("D")
def invvol(s, t0, c, f):
    e = entry(t0); r = (c / c.shift(1) - 1).loc[e - pd.Timedelta(hours=24):e - pd.Timedelta(hours=1)]
    v = float(r.std() * np.sqrt(24 * 365)) if len(r) > 5 else np.nan
    return float(np.clip(2.0 / v, 0.5, 2.0)) if np.isfinite(v) and v > 0 else 1.0
def crowded(s, t0, c, f):
    e = entry(t0); x = f.loc[e - pd.Timedelta(hours=24):e - pd.Timedelta(minutes=1)]
    return len(x) > 0 and float(x.mean()) * 8.0 / FI.get(s, 8.0) < -0.0005
base = pnl(sized(EV, lambda *a: 1.0)); V6 = V.assign(**{"listing short": base}); v96 = unit(CS.portfolio_v5(V6)[0])
EVB = [e for e in EV if not crowded(*e)]
T = {"A inverse-vol sizing": pnl(sized(EV, invvol)), "B skip crowded shorts": pnl(sized(EVB, lambda *a: 1.0))}
REF_R = (3.161, [2.775, 3.919, 2.576])
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing)": [shp(v96), per(v96)], "base sleeve": per(base), "events": len(EV), "events skipped by B": len(EV) - len(EVB), "trials": {}}
for k, s in T.items():
    b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "book": r, "pass": bool(r[0] >= REF_R[0] + 0.05 and all(r[1][i] >= REF_R[1][i] for i in range(3)))}
(ROOT / "results/gen428.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
