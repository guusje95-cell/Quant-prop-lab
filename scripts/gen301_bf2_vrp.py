"""Gen301 (config/gen301_protocol.json): bf2 spot ridge + VRP / calendar features. Writes results/gen301.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import bf2lab as F
import ridge_live as RL
END = F.END
D0 = RL.features(END, spot=True)


def run(D):
    D = D.copy(); D["y"] = D["target"]
    feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return F.cfd(D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5)


out = {"reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
base = run(D0); out["check: reproduces bf2 ridge"] = float((base - F.HB_RIDGE.reindex(base.index).fillna(0)).abs().max()); print(out, flush=True)
A = D0.copy(); vrp = pd.Series(np.nan, index=A.index)
for c in RL.COINS:
    m = A["coin"] == c; dv = RL.dvol(c) / 100 / np.sqrt(365)
    vrp[m] = A.loc[m, "day"].map(dv).to_numpy() - A.loc[m, "vol30"].to_numpy()
A["vrp"] = vrp; A["vrp7"] = A.groupby("coin")["vrp"].diff(7)
C = D0.copy(); dow = C["day"].dt.dayofweek; C["wkend"] = dow.isin([4, 5]).astype(float); C["mon"] = (dow == 6).astype(float)
for k, D in (("A VRP", A), ("B calendar", C)):
    F.judge(k, run(D), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(F.ROOT / "results/gen301.json", "w"), indent=1)
