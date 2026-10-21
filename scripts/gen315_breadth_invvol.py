"""Gen315 (config/gen315_protocol.json): 60-coin premium carry with inverse-vol legs in v8.4. Writes results/gen315.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
h = CS.premium_carry_breadth(w=CS.premium_breadth_weights(invvol=True)).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
s = L.per(h, "2020-01-01"); out["sleeve D/T/H"] = np.round(s, 3).tolist(); out["old sleeve D/T/H"] = np.round(L.per(L.H6["premium carry"], "2020-01-01"), 3).tolist()
H = L.H6.copy(); H["premium carry"] = h
b = L.CS.portfolio_v5(pd.concat([H, L.RIDGE] + L.ALTK, axis=1).fillna(0.0))[0]
B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out["v8.4 with 60-coin invvol carry"] = [round(B1, 3), np.round(k, 3).tolist()]
out["pass"] = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and B1 > L.REF[0] and k[1] >= L.REF[1][1] and k[2] >= L.REF[1][2])
print(out); json.dump(out, open(L.ROOT / "results/gen315.json", "w"), indent=1)
