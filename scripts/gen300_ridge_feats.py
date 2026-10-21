"""Gen300 (config/gen300_protocol.json): v8.3 ridge + VRP / breadth change / calendar features. Writes results/gen300.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
END = L.END
D0 = RL.features(END); D0["kb"] = D0["day"].map(AK.zscores(END + " 23:00").mean(axis=1))


def run(D):
    D = D.copy(); D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
    feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return L.perp(D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5)


out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
base = run(D0); out["check: reproduces v8.3 ridge"] = float((base - L.RIDGE.reindex(base.index).fillna(0)).abs().max()); print(out, flush=True)
A = D0.copy(); vrp = pd.Series(np.nan, index=A.index)
for c in RL.COINS:
    m = A["coin"] == c; dv = RL.dvol(c) / 100 / np.sqrt(365)
    vrp[m] = A.loc[m, "day"].map(dv).to_numpy() - A.loc[m, "vol30"].to_numpy()
A["vrp"] = vrp; A["vrp7"] = A.groupby("coin")["vrp"].diff(7)
B = D0.copy(); B["dkb"] = B.groupby("coin")["kb"].diff(7)
C = D0.copy(); dow = C["day"].dt.dayofweek; C["wkend"] = dow.isin([4, 5]).astype(float); C["mon"] = (dow == 6).astype(float)
for k, D in (("A VRP", A), ("B breadth change", B), ("C calendar", C)):
    L.judge(k, run(D), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen300.json", "w"), indent=1)
