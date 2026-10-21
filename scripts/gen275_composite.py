"""Gen275 (config/gen275_protocol.json): demand composite in v8.1 (added) and bf2 (replacing the Coinbase premium sleeve).
Writes results/gen275.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
import ridge_live as RL
END = L.END
D = RL.features(END); days = pd.DatetimeIndex(sorted(D["day"].unique())); W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    x = D[D["coin"] == c].set_index("day"); s = x[["zc", "zk"]].mean(axis=1, skipna=False)
    z = (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()
    W[c] = np.where(z > 1, 0.5, np.where(z < -1, -0.5, 0.0))
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
L.judge("A demand composite in v8.1", L.perp(W), out)
hc = F.cfd(W); HBc = F.HB0.copy(); HBc["coinbase premium"] = hc.reindex(HBc.index).fillna(0.0)
b = F.CS.portfolio_v5(pd.concat([HBc, F.IS0, F.HB_RIDGE.rename("ridge ML")], axis=1).fillna(0.0))[0]
B1, k1 = F.sh(b, "2022-01-01", END), F.per(b, "2022-01-01")
out["B bf2, composite replaces the Coinbase premium sleeve"] = {"composite sleeve D/T/H (CFD)": np.round(F.per(hc, "2020-01-01"), 3).tolist(),
    "old Coinbase sleeve D/T/H": np.round(F.per(F.HB0["coinbase premium"], "2020-01-01"), 3).tolist(), "bf2": [round(B1, 3), np.round(k1, 3).tolist()],
    "pass": bool(B1 > F.REF[0] and k1[1] >= F.REF[1][1] and k1[2] >= F.REF[1][2])}
print(out["B bf2, composite replaces the Coinbase premium sleeve"]); json.dump(out, open(L.ROOT / "results/gen275.json", "w"), indent=1)
