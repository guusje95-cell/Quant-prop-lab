"""Gen289 (config/gen289_protocol.json): inverse-vol sizing of the ridge and alt-kimchi sleeves (vs v8.2). Writes results/gen289.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END; days = pd.date_range("2020-01-01", END)
out = {"reference v8.2": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}


def judge(name, ridge_h, altk_h):
    b = L.CS.portfolio_v5(pd.concat([L.H6, ridge_h.rename("ridge ML"), altk_h.rename("alt kimchi")], axis=1).fillna(0.0))[0]
    B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
    out[name] = {"book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
    print(name, out[name], flush=True)


vol = lambda coins: B.panel("close", "1D", coins).reindex(days).pct_change(fill_method=None).rolling(30).std()
# A: ridge
D = RL.predictions(END, kb=True, volscale=True); P = D.pivot(index="day", columns="coin", values="ridge").reindex(days).fillna(0.0)
v = vol(["BTC", "ETH"]); ref = v.stack().groupby(level=0).median().rolling(365, min_periods=180).median()
wA = 0.5 * P * (v.rdiv(ref, axis=0)).clip(0.5, 2).fillna(1.0)
judge("A ridge inverse-vol sizing", L.perp(wA), L.ALTK[0])
# B: alt kimchi
z = AK.zscores(END + " 23:00").reindex(days); sgn = np.sign(z.where(z.abs() > 1)).fillna(0.0)
va = vol(list(z.columns)); refa = va.median(axis=1).rolling(365, min_periods=180).median()
wB = 0.1 * sgn * (va.rdiv(refa, axis=0)).clip(0.5, 2).fillna(1.0)
judge("B alt-kimchi inverse-vol sizing", L.RIDGE, L.perp(wB))
json.dump(out, open(L.ROOT / "results/gen289.json", "w"), indent=1)
