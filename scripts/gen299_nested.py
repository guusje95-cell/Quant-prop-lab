"""Gen299 (config/gen299_protocol.json): nested (2020-22 only) tuning of alt-kimchi threshold, premium-carry window, ridge alpha.
Writes results/gen299.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, CS, END = L.B, L.CS, L.END
dev = lambda h, a="2020-01-01": L.sh(h, a, "2022-12-31")
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "grid (selection metric: sleeve Sharpe on DEV only)": {}}
G = out["grid (selection metric: sleeve Sharpe on DEV only)"]
# 1 alt kimchi threshold
z = AK.zscores(END + " 23:00"); res = {}
for th in (0.75, 1.0, 1.25, 1.5):
    h = L.perp(pd.DataFrame(np.where(z > th, 0.1, np.where(z < -th, -0.1, 0.0)), index=z.index, columns=z.columns)); res[th] = (dev(h), h)
G["alt kimchi threshold"] = {k: round(v[0], 3) for k, v in res.items()}; th_best = max(res, key=lambda k: (res[k][0], k == 1.0)); h_ak = res[th_best][1].rename("alt kimchi")
# 2 premium carry window (inverse-vol legs)
res = {}
for n in (3, 7, 14, 21):
    h = CS._from_daily_weights(CS.premium_weights(look=n, hold=n, invvol=True), B.coins(), 5); res[n] = (dev(h), h)
G["premium carry look = hold"] = {k: round(v[0], 3) for k, v in res.items()}; n_best = max(res, key=lambda k: (res[k][0], k == 7)); h_pc = res[n_best][1]
# 3 ridge alpha
D = RL.features(END); D["kb"] = D["day"].map(z.mean(axis=1)); D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]
def ridge(alpha):
    pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=alpha).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return L.perp(D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5)
res = {}
for a in (3.0, 10.0, 30.0, 100.0):
    h = ridge(a); res[a] = (dev(h, "2021-01-01"), h)
G["ridge alpha"] = {k: round(v[0], 3) for k, v in res.items()}; a_best = max(res, key=lambda k: (res[k][0], k == 10.0)); h_rg = res[a_best][1].rename("ridge ML")
out["selected"] = {"alt kimchi threshold": th_best, "premium carry window": n_best, "ridge alpha": a_best}
print(out["grid (selection metric: sleeve Sharpe on DEV only)"], out["selected"], flush=True)
H = L.H6.copy(); H["premium carry"] = h_pc.reindex(H.index).fillna(0.0)
b = CS.portfolio_v5(pd.concat([H, h_rg, h_ak], axis=1).fillna(0.0))[0]; B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out["book with selected settings"] = [round(B1, 3), np.round(k1, 3).tolist()]
out["pass"] = bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])
print(out["book with selected settings"], out["pass"]); json.dump(out, open(L.ROOT / "results/gen299.json", "w"), indent=1)
