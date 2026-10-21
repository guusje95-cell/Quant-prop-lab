"""Gen291 (config/gen291_protocol.json): Huber ridge; raw + vol-scaled ensemble (vs v8.2). Writes results/gen291.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
END = L.END; out = {"reference v8.2": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
D = RL.features(END); D["kb"] = D["day"].map(AK.zscores(END + " 23:00").mean(axis=1))
D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
    te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = HuberRegressor(epsilon=1.35, alpha=10.0 / len(tr), max_iter=500).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
wA = D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
L.judge("A Huber regression", L.perp(wA), out, dev_start="2021-01-01", replace_ridge=True)
p_raw = RL.predictions(END, kb=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0)
p_vs = RL.predictions(END, kb=True, volscale=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0)
L.judge("B raw + vol-scaled ensemble", L.perp(0.5 * (p_raw + p_vs) / 2), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen291.json", "w"), indent=1)
