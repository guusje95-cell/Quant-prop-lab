"""Gen464 (config/gen464_protocol.json): relative retail crowding among new listings (market neutral). Writes results/gen464.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"; ARCH = ROOT / "data/lab/binance_vision"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, EV = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
X, CF = {}, {}
for s, t0, c, f in EV:
    m = ARCH / f"{s}_metrics.parquet"
    if not m.exists():
        continue
    x = pd.read_parquet(m, columns=["time", "count_long_short_ratio"]); x["time"] = pd.to_datetime(x["time"])
    x = x.set_index("time")["count_long_short_ratio"].astype(float); x = x[(x.index >= t0 + pd.Timedelta(days=2)) & (x.index < t0 + pd.Timedelta(days=41))]
    g = x.groupby(x.index.floor("D")); daily = g.mean().where(g.count() >= 200)
    if daily.notna().sum():
        X[s[:-4]] = np.log(daily.where(daily > 0)); CF[s[:-4]] = (c, f)
D = pd.DataFrame(X)
n_ok = D.notna().sum(axis=1)
score = D.sub(D.mean(axis=1), axis=0).where(n_ok >= 3)
W = (-0.05 * (score / 0.5).clip(-2, 2) / 2).fillna(0.0)
P = W.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)        # day d decided at its close, held during d + 1
g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
s_ = pd.Series(0.0, index=idx)
for n in P.columns:
    c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
b = unit(CS.portfolio_v5(V7.assign(**{"new-coin crowding": s_}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "coins": D.shape[1], "days with >= 3 coins by year": {str(y): int(v) for y, v in (n_ok >= 3).groupby(n_ok.index.year).sum().items()},
       "sleeve": per(s_), "by year": {str(y): shp(s_, str(y), str(y)) for y in range(2022, 2027)}, "corr listing short": round(float(dd(s_).corr(dd(ls))), 2),
       "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen464.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
