"""H1b (research/v99/h1_protocol.json): neighbourhood + per-period check of the flagged H1 event-short vol-regime rule.
Writes results/v99/h1_robustness.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = "2026-09-30"
H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else float("nan")
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
btc = B.k5("BTC").close.resample("1D").last(); r = btc.pct_change()
def regime(win, q):
    vol = r.rolling(win).std()
    return (vol > vol.rolling(365, min_periods=180).quantile(q)).shift(1).fillna(False)
b0 = unit(CS.portfolio_v5(H)[0]); REF = [shp(b0), per(b0)]
cells = []
for win in (20, 30, 60):
    for q in (0.5, 0.6):
        hi = regime(win, q)
        for sc in (0.5, 0.0):
            s = hi.map({True: sc, False: 1.0}).reindex(H.index.floor("D")).set_axis(H.index).fillna(1.0)
            b = unit(CS.portfolio_v5(H.assign(**{"listing short": H["listing short"] * s}))[0]); v = [shp(b), per(b)]
            cells.append({"window": win, "quantile": q, "scale": sc, "book": v, "gain": round(v[0] - REF[0], 3),
                          "pass": bool(v[0] >= REF[0] + 0.05 and all(v[1][i] >= REF[1][i] for i in range(3)))})
            print(cells[-1], flush=True)
hi = regime(30, 0.5).reindex(H.index.floor("D")).set_axis(H.index).fillna(False).astype(bool)
ev = H["listing short"]
split = {}
for lab, a, z in (("2022", "2022", "2022"), ("2023-24", "2023", "2024"), ("2025-26", "2025", END)):
    x = ev.loc[a:z]; m = hi.loc[a:z]
    split[lab] = {"high-vol days": shp(x.where(m, 0.0), a, z), "low-vol days": shp(x.where(~m, 0.0), a, z)}
npass = sum(c["pass"] for c in cells); med = float(np.median([c["gain"] for c in cells]))
weaker = all(v["high-vol days"] < v["low-vol days"] for v in split.values())
out = {"reference v9.8": REF, "cells": cells, "cells passing": npass, "median gain": round(med, 3), "event short by regime (30d, median)": split,
       "sleeve weaker in high vol in every period": weaker, "robust": bool(npass >= 10 and med >= 0.05 and weaker), "flag": "post hoc (Gen473)"}
(ROOT / "results/v99/h1_robustness.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("reference v9.8", "cells passing", "median gain", "event short by regime (30d, median)", "robust")}, indent=1))
