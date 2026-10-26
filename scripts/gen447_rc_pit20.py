"""Gen447 (config/gen447_protocol.json): relative crowding on the point-in-time top-20 as a second sleeve. Writes results/gen447.json."""
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
mem = PU.members(20).reindex(days).fillna(False)
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
COLS = ("count_toptrader_long_short_ratio", "count_long_short_ratio")
R = {c: PU.ratios(c) for c in mem.columns if mem[c].any()}
R = {c: r for c, r in R.items() if r is not None and all(k in r for k in COLS)}
def daily_w(col, smooth=False):
    Z = {}
    for c, r in R.items():
        s = r[col].astype(float); s.index = pd.DatetimeIndex(s.index).floor("D"); s = s.groupby(level=0).mean().reindex(days).ffill().shift(1)
        Z[c] = z(s, 90)
    Z = pd.DataFrame(Z).where(mem[list(R)].shift(1).fillna(False))
    Zd = Z.sub(Z.mean(axis=1), axis=0); W = (-0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)
    return W.rolling(3, min_periods=1).mean() if smooth else W
def h8_pos(col):
    Z = {}
    for c, r in R.items():
        x = r[col].astype(float).resample("8h").mean(); Z[c] = (x - x.rolling(270, min_periods=190).mean()) / x.rolling(270, min_periods=190).std()
    Z = pd.DataFrame(Z); m8 = mem[list(R)].reindex(Z.index.floor("D")).set_axis(Z.index).fillna(False)
    Z = Z.where(m8); Zd = Z.sub(Z.mean(axis=1), axis=0); W = (-0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)
    W.index = W.index + pd.Timedelta(hours=8); return W.reindex(idx, method="ffill").fillna(0.0)
P = 0.0
for col in COLS:
    for sm in (False, True):
        P = P + daily_w(col, sm).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0) / 6
    P = P + h8_pos(col) / 6
s = PU.pnl_from_hourly_positions(P, idx, 5.0)
b = unit(CS.portfolio_v5(V6.assign(**{"relative crowding top-20": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "coins with ratios": len(R), "sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)},
       "corr with the 6-coin sleeve": round(float(s.corr(V6["relative crowding 6"])), 2), "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen447.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
