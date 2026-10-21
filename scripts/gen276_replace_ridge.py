"""Gen276 (config/gen276_protocol.json): v8.1 with the demand composite instead of the ridge. Writes results/gen276.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
END = L.END
D = RL.features(END); days = pd.DatetimeIndex(sorted(D["day"].unique())); W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    x = D[D["coin"] == c].set_index("day"); s = x[["zc", "zk"]].mean(axis=1, skipna=False)
    z = (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std(); W[c] = np.where(z > 1, 0.5, np.where(z < -1, -0.5, 0.0))
b = L.CS.portfolio_v5(pd.concat([L.H6, L.perp(W).rename("demand composite")] + L.ALTK, axis=1).fillna(0.0))[0]
B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "composite instead of ridge": [round(B1, 3), np.round(k1, 3).tolist()],
       "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen276.json", "w"), indent=1)
