"""Gen446 (config/gen446_protocol.json): deleveraging bounce on the point-in-time top-20 / top-50. Writes results/gen446.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import pit_universe as PU
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
days = pd.date_range("2021-12-01", END)
def signal(c):                                               # CS.delev_bounce_weights rule for one coin (decided at 23:55 UTC of day d)
    d = PU.frame(c)
    if d is None:
        return None
    m = d["oi"].where(d["oi"] > 0).ffill(); px = d["c"]
    t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
    f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
    sig = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -0.10) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=days)
    return sig.astype(float).rolling(2, min_periods=1).max()
def sleeve(n):
    mem = PU.members(n).reindex(days).fillna(False); W = {}
    for c in [c for c in mem.columns if mem[c].any()]:
        s = signal(c)
        if s is not None:
            W[c] = s.where(mem[c], 0.0)
    W = pd.DataFrame(W).fillna(0.0) * (0.5 / n)
    P = W.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)            # row d held during d + 1
    return PU.pnl_from_hourly_positions(P, idx, 5.0)
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "current delev bounce (BTC/ETH)": per(V6["delev bounce"]), "trials": {}}
for k, n in (("A delev bounce point-in-time top-20", 20), ("B delev bounce point-in-time top-50", 50)):
    s = sleeve(n); b = unit(CS.portfolio_v5(V6.assign(**{"delev bounce": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book": r, "pass": bool(ok(r, REF))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen446.json").write_text(json.dumps(out, indent=1))
