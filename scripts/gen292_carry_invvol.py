"""Gen292 (config/gen292_protocol.json): inverse-vol premium carry in v8.2 and bf2. Writes results/gen292.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
B, CS, END = L.B, L.CS, L.END


def weights(C, look=7, hold=7):
    P = B.panel("close", "1D", C)
    prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60; vol = P.pct_change(fill_method=None).rolling(30).std(); iv = (1 / vol).where(listed)
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    lo, hi = (rk > 2 / 3), (rk <= 1 / 3)
    wl = iv.where(lo, 0.0); ws = iv.where(hi, 0.0)
    w = wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


out = {"reference v8.2": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
w = weights(B.coins()); H = L.H6.copy(); H["premium carry"] = CS._from_daily_weights(w, B.coins(), 5).reindex(H.index).fillna(0.0)
b = CS.portfolio_v5(pd.concat([H, L.RIDGE] + L.ALTK, axis=1).fillna(0.0))[0]; B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out["v8.2"] = {"book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}; print("v8.2", out["v8.2"], flush=True)
wc = weights(F.CB.CFD).reindex(columns=F.CB.CFD).fillna(0.0); HB = F.HB0.copy(); HB["premium carry"] = F.cfd(wc).reindex(HB.index).fillna(0.0)
b2 = CS.portfolio_v5(pd.concat([HB, F.IS0, F.HB_RIDGE.rename("ridge ML")], axis=1).fillna(0.0))[0]; B2, k2 = F.sh(b2, "2022-01-01", END), F.per(b2, "2022-01-01")
out["bf2"] = {"book": [round(B2, 3), np.round(k2, 3).tolist()], "pass": bool(B2 > F.REF[0] and k2[1] >= F.REF[1][1] and k2[2] >= F.REF[1][2])}; print("bf2", out["bf2"], flush=True)
json.dump(out, open(L.ROOT / "results/gen292.json", "w"), indent=1)
