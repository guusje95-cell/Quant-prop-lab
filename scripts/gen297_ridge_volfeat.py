"""Gen297 (config/gen297_protocol.json): v8.3 ridge with vol-normalised return features. Writes results/gen297.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
END = L.END
D = RL.features(END); D["kb"] = D["day"].map(AK.zscores(END + " 23:00").mean(axis=1))
for n in (1, 3, 7, 30):
    D[f"r{n}"] = D[f"r{n}"] / (D["vol30"] * np.sqrt(n)).replace(0, np.nan)
D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
    te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
w = D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
L.judge("vol-normalised return features", L.perp(w), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen297.json", "w"), indent=1)
