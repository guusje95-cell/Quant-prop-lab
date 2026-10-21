"""Gen292 checks (descriptive): inverse-vol premium carry in v8.2 - vol windows, cost, weight cap. Writes results/gen292_check.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, CS, END = L.B, L.CS, L.END; C = B.coins()
P = B.panel("close", "1D", C); prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(7).mean()
listed = P.notna().cumsum() >= 60; rk = (-prem).where(listed).rank(axis=1, pct=True); lo, hi = (rk > 2 / 3), (rk <= 1 / 3)
def weights(vw=30, cap=None):
    iv = (1 / P.pct_change(fill_method=None).rolling(vw).std()).where(listed)
    def leg(m):
        x = iv.where(m, 0.0); x = x.div(x.sum(axis=1), axis=0)
        if cap:
            eq = m.astype(float).div(m.sum(axis=1), axis=0); x = x.clip(upper=cap * eq); x = x.div(x.sum(axis=1), axis=0)
        return x
    w = leg(lo) - leg(hi)
    return w.where(pd.Series(np.arange(len(w)) % 7 == 0, index=w.index), np.nan).ffill().fillna(0.0)
out = {"reference v8.2": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
def run(name, w, cost=5):
    H = L.H6.copy(); H["premium carry"] = CS._from_daily_weights(w, C, cost).reindex(H.index).fillna(0.0)
    b = CS.portfolio_v5(pd.concat([H, L.RIDGE] + L.ALTK, axis=1).fillna(0.0))[0]
    out[name] = [round(L.sh(b, "2022-01-01", END), 3), np.round(L.per(b, "2022-01-01"), 3).tolist(),
                 "sleeve D/T/H", np.round(L.per(H["premium carry"], "2020-01-01"), 3).tolist()]; print(name, out[name], flush=True)
w0 = weights(); run("adopted candidate (30d)", w0); run("14-day vol", weights(14)); run("60-day vol", weights(60))
run("weight cap 2x equal", weights(cap=2.0)); run("2x costs (10 bp)", w0, cost=10)
eqw = (lo.astype(float).div(lo.sum(axis=1), axis=0) - hi.astype(float).div(hi.sum(axis=1), axis=0))
eqw = eqw.where(pd.Series(np.arange(len(eqw)) % 7 == 0, index=eqw.index), np.nan).ffill().fillna(0.0)
run("equal weights (current), for comparison", eqw)
json.dump(out, open(L.ROOT / "results/gen292_check.json", "w"), indent=1)
