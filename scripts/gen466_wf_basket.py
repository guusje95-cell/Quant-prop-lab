"""Gen466 (config/gen466_protocol.json): walk-forward second basket over the whole pool. Writes results/gen466.json."""
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
POOL = pd.read_parquet(ROOT / "results/gen466_pool.parquet").reindex(idx).fillna(0.0)
D = dd(POOL)
W = pd.DataFrame(0.0, index=D.index, columns=D.columns); members = {}
for q in D.index[~D.index.to_period("Q").duplicated()]:
    hist = D.loc["2021-06-01":q - pd.Timedelta(days=1)]
    if len(hist) < 30:
        continue
    nz = (hist != 0).sum(); sr = hist.mean() / hist.std() * np.sqrt(365)
    keep = [c for c in D.columns if nz[c] >= 180 and sr[c] > 0.5]
    members[str(q.date())] = keep
    if keep:
        sd = D.loc[q - pd.Timedelta(days=365):q - pd.Timedelta(days=1), keep].std()
        w = (1.0 / sd).replace([np.inf], 0.0).fillna(0.0) / len(keep)
        end = q + pd.offsets.QuarterEnd(0)
        W.loc[q:end, keep] = w.to_numpy()
Wh = W.reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
bh = unit((POOL * Wh).sum(axis=1))
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
b = unit(CS.portfolio_v5(V7.assign(**{"second basket (walk-forward)": bh}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "pool": {c: per(POOL[c]) for c in POOL.columns}, "members per quarter": members,
       "basket": per(bh), "by year": {str(y): shp(bh, str(y), str(y)) for y in range(2022, 2027)}, "corr diversifier basket": round(float(dd(bh).corr(dd(V7["diversifier basket"]))), 2),
       "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
bh.to_frame("wf basket").to_parquet(ROOT / "results/gen466_basket_hourly.parquet")
(ROOT / "results/gen466.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("basket", "by year", "corr diversifier basket", "book", "pass")}, indent=1))
