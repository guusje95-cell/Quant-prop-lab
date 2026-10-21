"""Gen286 (config/gen286_protocol.json): strategy momentum on v8.1 sleeves. Writes results/gen286.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
D = H.groupby(H.index.floor("D")).sum()
M = (D.rolling(90, min_periods=60).sum().shift(1) > 0).astype(float).replace(0.0, 0.5)
M = M.where(D.rolling(90, min_periods=60).sum().shift(1).notna(), 1.0)
Hm = H * M.reindex(H.index.floor("D")).set_axis(H.index).to_numpy()
bk = L.CS.portfolio_v5(Hm)[0]; B1, k1 = L.sh(bk, "2022-01-01", END), L.per(bk, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "share of sleeve-days at half weight": round(float((M == 0.5).mean().mean()), 3),
       "book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen286.json", "w"), indent=1)
