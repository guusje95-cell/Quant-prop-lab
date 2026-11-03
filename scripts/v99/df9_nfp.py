"""DF-9 (research/v99/df9_protocol.json). Writes results/v99/df9_nfp.json."""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat
F = dailyflat.patch()
import fbook
g = {"__file__": str(ROOT / "scripts/gen203_universe.py"), "__name__": "g203"}
exec((ROOT / "scripts/gen203_universe.py").read_text().split("\nres = {}")[0], g)
IX, daily_book = g["IX"], g["daily_book"]


def nfp_dates(a=2009, b=2026):
    out = []
    for y in range(a, b + 1):
        for m in range(1, 13):
            d12 = pd.Timestamp(y, m, 12); sat = d12 + pd.Timedelta(days=(5 - d12.weekday()) % 7)
            out.append(sat + pd.Timedelta(days=20))
    return pd.DatetimeIndex(out)


N = nfp_dates(); assert pd.Timestamp("2024-10-04") in N and pd.Timestamp("2024-09-06") in N and pd.Timestamp("2025-02-07") in N
mask = pd.Series(IX.isin(N).astype(float), index=IX)
nfp = daily_book(pd.DataFrame({r: mask * 0.5 for r in ("ES", "NQ")}), ["ES", "NQ"])
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
Q2 = Q.copy(); Q2["NFP"] = nfp.reindex(Q.index).fillna(0.0)
out = {"NFP days in data": int(mask.sum()), "NFP sleeve": per(Q2["NFP"]), "NFP-day mean ES+NQ return (bp)": round(float(nfp[nfp != 0].mean() * 1e4), 2),
       "equity book ref": per(fbook.build(Q)), "equity book + NFP": per(fbook.build(Q2))}
out["pass"] = bool(out["equity book + NFP"][2] >= out["equity book ref"][2] + 0.05 and out["equity book + NFP"][1] >= out["equity book ref"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df9_nfp.json").write_text(json.dumps(out, indent=1))
