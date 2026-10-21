"""Gen285 (config/gen285_protocol.json): weekly altcoin kimchi replacing v8.1's daily sleeve. Writes results/gen285.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END; days = pd.date_range("2020-01-01", END); fx = RL.usdkrw(); W = {}
for c in AK.coins():
    up = RL.upbit(c); bn = B.k5(c).close.resample("1h").last()
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END + " 23:00"]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D"); kd = kd.reindex(days)
    z = (kd.rolling(7, min_periods=5).mean() - kd.rolling(90, min_periods=60).mean()) / kd.rolling(90, min_periods=60).std()
    w = pd.Series(np.where(z > 1, 0.1, np.where(z < -1, -0.1, 0.0)), index=days)
    W[c] = w.where(days.dayofweek == 6).ffill().fillna(0.0)           # decided on Sundays, held the following week
W = pd.DataFrame(W)
h = L.perp(W).rename("alt kimchi")
bk = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, h], axis=1).fillna(0.0))[0]
B1, k1 = L.sh(bk, "2022-01-01", END), L.per(bk, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "weekly sleeve D/T/H": np.round(L.per(h, "2020-01-01"), 3).tolist(),
       "book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen285.json", "w"), indent=1)
