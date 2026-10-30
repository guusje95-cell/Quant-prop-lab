"""Gen477 (config/gen477_protocol.json): FRED market macro signals as futures-book sleeves. Writes results/gen477.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
import futures_db as F


def fred(s):
    d = pd.read_csv(ROOT / f"research_data/fred/{s}.csv"); d.columns = ["date", "v"]
    return pd.Series(pd.to_numeric(d["v"], errors="coerce").to_numpy(), index=pd.to_datetime(d["date"])).dropna()


def usable(sig, idx):
    """value of day t -> position from the close of the next trading day (one-day publication lag), held until replaced"""
    return sig.reindex(idx.union(sig.index)).ffill().reindex(idx).shift(1)


def sleeve(pos_by_root):
    legs = []
    for root, pos in pos_by_root.items():
        d = F.daily(root); vol = d.r.rolling(60, min_periods=40).std() * np.sqrt(252)
        w = (usable(pos, d.index).fillna(0.0) * (0.10 / vol).clip(upper=3.0)).fillna(0.0).shift(1).fillna(0.0)
        legs.append(w * d.r - w.diff().abs().fillna(w.abs()) * d.cost)
    return pd.concat(legs, axis=1).fillna(0.0).mean(axis=1)


slope = fred("DGS10").sub(fred("DGS3MO")).dropna()
z = ((slope - slope.rolling(756, min_periods=500).mean()) / slope.rolling(756, min_periods=500).std()).clip(-1, 1)
baa = fred("BAA10Y"); m2 = (baa.diff(21) < 0).astype(float).where(baa.diff(21).notna())
ry = fred("DFII10"); m3 = -np.sign(ry.diff(21))
be = fred("T10YIE"); m4 = np.sign(be.diff(63))
S = {"M1 curve slope -> Treasuries": sleeve({"ZN": z, "ZB": z}),
     "M2 credit spread -> equities": sleeve({"ES": m2, "NQ": m2}),
     "M3 real-yield momentum -> gold": sleeve({"GC": m3}),
     "M4 breakeven momentum -> commodities": sleeve({"CL": m4, "HG": m4, "GC": m4})}
base = fbook.sleeves(); bk = fbook.build(base); ref = [round(F.sharpe(bk, *s), 3) for s in F.SPLITS]
out = {"reference": ref, "trials": {}}; entrants = {}
for k, p in S.items():
    tune = round(F.sharpe(p, "2010-06-01", "2022-12-31"), 3)
    b = fbook.build(base.assign(**{k: p})); r = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
    e = bool(tune >= 0.3)
    out["trials"][k] = {"sleeve 2010-17 / 2018-22 / 2023-26": list(F.splits(p)), "tune": tune, "appraisal ES/NQ 2010-22": round(fbook.appraisal(p), 3),
                        "corr with book 2023-26": round(float(pd.concat([p, bk], axis=1, sort=True).loc["2023":].corr().iloc[0, 1]), 2),
                        "enters": e, "book": r, "pass": bool(e and r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])}
    if e:
        entrants[k] = p
    print(k, out["trials"][k], flush=True)
if len(entrants) > 1:
    b = fbook.build(base.assign(**entrants)); out["all entrants together"] = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out["passed"] = [k for k, v in out["trials"].items() if v["pass"]]
(ROOT / "results/gen477.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in out if k != "trials"}, indent=1))
