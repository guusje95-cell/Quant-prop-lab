"""Gen296 (config/gen296_protocol.json): inverse-vol R1 / P1 legs in bf2's index sleeve. Writes results/gen296.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import index_sleeve as IS
IDX = F.IDXbf; L_ = IS.legs(IDX)
vol = {}
for s in ("US100", "US500", "US30"):
    x = IS.hourly(s)["close"].reindex(IDX).ffill(limit=72); r = x.pct_change().fillna(0.0)
    vol[s] = r.groupby(r.index.floor("D")).sum().rolling(20).std().shift(1)
V = pd.DataFrame(vol); ref = V.median(axis=1); mult = V.rdiv(ref, axis=0).clip(0.5, 2).fillna(1.0)
Mh = mult.reindex(IDX.floor("D")).set_axis(IDX)
rets = {s: IS.hourly(s)["close"].reindex(IDX).ffill(limit=72).pct_change().fillna(0.0) for s in ("US100", "US500", "US30")}
tot = L_["P6"][1].copy()
for leg in ("R1", "P1"):
    pos = L_[leg][0]
    for s in pos.columns:
        w = pos[s] * Mh[s]
        tot = tot + w * rets[s] - w.diff().abs().fillna(0.0) * IS.COST
b = F.CS.portfolio_v5(pd.concat([F.HB0, tot.rename("vol-managed indices"), F.HB_RIDGE.rename("ridge ML")], axis=1).fillna(0.0))[0]
B1, k1 = F.sh(b, "2022-01-01", F.END), F.per(b, "2022-01-01")
out = {"reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "book": [round(B1, 3), np.round(k1, 3).tolist()],
       "pass": bool(B1 > F.REF[0] and k1[1] >= F.REF[1][1] and k1[2] >= F.REF[1][2])}
print(out); json.dump(out, open(F.ROOT / "results/gen296.json", "w"), indent=1)
