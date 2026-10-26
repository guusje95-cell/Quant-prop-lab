"""Gen433 (config/gen433_protocol.json): C* in v9.6. Writes results/gen433.json."""
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
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0])
def weighted(Hk, col, m):
    ph0, W, mult = CS.portfolio_v5(Hk); W2 = W.copy(); W2[col] *= m
    Wh = W2.reindex(Hk.index.floor("D")).set_axis(Hk.index); raw = (Hk * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    tgt = (0.15 / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    return unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
REF_R = (3.161, [2.775, 3.919, 2.576])
T = {"A v9.6 without C*": unit(CS.portfolio_v5(V6.drop(columns="C*"))[0]), "B C* at half weight": weighted(V6, "C*", 0.5)}
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing)": [shp(v96), per(v96)], "check weighted x1": [shp(weighted(V6, "C*", 1.0)), per(weighted(V6, "C*", 1.0))], "trials": {}}
for k, b in T.items():
    r = [shp(b), per(b)]; out["trials"][k] = {"book": r, "pass": bool(r[0] >= REF_R[0] + 0.05 and all(r[1][i] >= REF_R[1][i] for i in range(3)))}
(ROOT / "results/gen433.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
