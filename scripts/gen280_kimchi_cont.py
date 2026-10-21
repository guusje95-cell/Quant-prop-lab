"""Gen280 (config/gen280_protocol.json): continuous alt-kimchi sizing replacing the threshold sleeve. Writes results/gen280.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import alt_kimchi as AK
END = L.END
z = AK.zscores(END + " 23:00"); w = (0.1 * (z / 2).clip(-1, 1)).fillna(0.0)
h = L.perp(w).rename("alt kimchi")
bk = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, h], axis=1).fillna(0.0))[0]
B1, k1 = L.sh(bk, "2022-01-01", END), L.per(bk, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "continuous sleeve D/T/H": np.round(L.per(h, "2020-01-01"), 3).tolist(),
       "threshold sleeve D/T/H": np.round(L.per(L.ALTK[0], "2020-01-01"), 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
       "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen280.json", "w"), indent=1)
