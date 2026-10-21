"""Gen293 (config/gen293_protocol.json): inverse-vol cascade and deleveraging bounce (vs v8.3). Writes results/gen293.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, CS, END = L.B, L.CS, L.END
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
def judge(name, col, h):
    H = L.H6.copy(); H[col] = h.reindex(H.index).fillna(0.0)
    b = CS.portfolio_v5(pd.concat([H, L.RIDGE] + L.ALTK, axis=1).fillna(0.0))[0]; B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
    out[name] = {"book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
    print(name, out[name], flush=True)
C = B.coins(); vol = B.panel("close", "1D", C).pct_change(fill_method=None).rolling(30).std().shift(1)
ref = vol.median(axis=1).rolling(365, min_periods=180).median()
def size_fn(coin, t0):
    d = pd.Timestamp(t0).floor("D")
    if d not in vol.index or not np.isfinite(vol.at[d, coin]) or not np.isfinite(ref.get(d, np.nan)):
        return 1.0
    return float(np.clip(ref[d] / vol.at[d, coin], 0.5, 2.0))
judge("A cascade inverse-vol", "cascade limit strict", CS.cascade(limit=0.005, through=0.001, size_fn=size_fn))
w = CS.delev_bounce_weights(); vb = B.panel("close", "1D", ["BTC", "ETH"]).pct_change(fill_method=None).rolling(30).std().reindex(w.index)
rb = vb.median(axis=1).rolling(365, min_periods=180).median()
w2 = w * vb.rdiv(rb, axis=0).clip(0.5, 2).fillna(1.0)
judge("B delev bounce inverse-vol", "delev bounce", CS._from_daily_weights(w2, ["BTC", "ETH"], 5))
json.dump(out, open(L.ROOT / "results/gen293.json", "w"), indent=1)
