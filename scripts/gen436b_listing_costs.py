"""Gen436b (descriptive): v9.6 A..Z listing-short robustness to costs (10 / 20 / 30 bp per side) and a one-day-later entry. Writes results/gen436b.json."""
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
v95 = unit(CS.portfolio_v5(V)[0]); out = {"v9.5": [shp(v95), per(v95)]}
EV = LL.events()
for nm, cost, shift_days in (("10 bp (v9.6)", 10.0, 0), ("20 bp", 20.0, 0), ("30 bp", 30.0, 0), ("entry one day later", 10.0, 1)):
    LL.COST_BP = cost
    EVx = [(s, t0 + pd.Timedelta(days=shift_days), c, f) for s, t0, c, f in EV]
    pos = LL.positions(idx, EVx); s = pd.Series(0.0, index=idx)
    for sym, t0, c, f in EVx:
        n = sym[:-4]
        if n not in pos:
            continue
        p = pos[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        s = s + p * r - p * fu - p.diff().abs().fillna(p.abs()) * cost / 1e4
    b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0])
    out[nm] = {"sleeve": per(s), "book": [shp(b), per(b)]}; print(nm, out[nm], flush=True)
(ROOT / "results/gen436b.json").write_text(json.dumps(out, indent=1))
