"""Gen298 (config/gen298_protocol.json): deleveraging bounce with an OI-drop z-score trigger (vs v8.3). Writes results/gen298.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, CS, END = L.B, L.CS, L.END
days = pd.date_range("2021-12-01", pd.Timestamp(END).normalize()); W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]); n = {}
for c in ("BTC", "ETH"):
    m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
    t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5); f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
    d = pd.Series(f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1, index=days); z = d / d.shift(1).rolling(90, min_periods=60).std()
    sig = (z < -2.5) & pd.Series(f(px, t) < f(px, t - pd.Timedelta(days=1)), index=days)
    W[c] = sig.astype(float).rolling(2, min_periods=1).max() * 0.5; n[c] = int(sig.sum())
H = L.H6.copy(); H["delev bounce"] = CS._from_daily_weights(W, ["BTC", "ETH"], 5).reindex(H.index).fillna(0.0)
b = CS.portfolio_v5(pd.concat([H, L.RIDGE] + L.ALTK, axis=1).fillna(0.0))[0]; B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
old = CS.delev_bounce_weights(); n_old = {c: int(((old[c] > 0) & (old[c].shift(1).fillna(0) == 0)).sum()) for c in ("BTC", "ETH")}
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "signals (z rule)": n, "episodes (current rule)": n_old,
       "book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen298.json", "w"), indent=1)
