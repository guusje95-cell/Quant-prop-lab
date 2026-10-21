"""Gen268 (config/gen268_protocol.json): ridge + kimchi breadth, v8 and bf2. Writes results/gen268.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import bf2lab as F
import ridge_live as RL
import alt_kimchi as AK
END = L.END
kb = AK.zscores(END + " 23:00").mean(axis=1)
out = {"reference v8": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}


def walk(spot):
    D = RL.features(END, spot); D["kb"] = D["day"].map(kb)
    feats = [x for x in D.columns if x not in ("day", "target", "coin")]; pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5


L.judge("ridge + kimchi breadth (v8)", L.perp(walk(False)), out, dev_start="2021-01-01", replace_ridge=True)
F.judge("ridge + kimchi breadth", F.cfd(walk(True)), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen268.json", "w"), indent=1)
