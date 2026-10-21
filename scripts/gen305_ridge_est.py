"""Gen305 (config/gen305_protocol.json): weekly refit (A) and alpha ensemble (B) for the v8.4 / bf2.2 ridges. Writes results/gen305.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import ridge_live as RL
import v7lab as L
import bf2lab as F
END = L.END


def walk(D, volscale, freq="MS", alphas=(10.0,)):
    D = D.copy(); D["y"] = D["target"] / D["vol30"].replace(0, np.nan) if volscale else D["target"]
    feats = [x for x in D.columns if x not in ("day", "target", "coin", "y", "ridge")]; pred = pd.Series(np.nan, index=D.index)
    starts = list(pd.date_range("2021-01-01", END, freq=freq))
    if starts[0] > pd.Timestamp("2021-01-01"):
        starts = [pd.Timestamp("2021-01-01")] + starts
    for i, m in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else pd.Timestamp(END) + pd.Timedelta(days=1)
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < nxt)]
        if len(te) == 0:
            continue
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        ps = []
        for a in alphas:
            mdl = Ridge(alpha=a).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
            ps.append(np.clip(mdl.predict(Xte) / s, -1, 1))
        pred.loc[te.index] = np.mean(ps, axis=0)
    return D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5


out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
DV = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).drop(columns=["y"])
DB = RL.predictions(END, spot=True, vrp=True, cal=True).drop(columns=["y"])
out["check v8.4"] = float((L.perp(walk(DV, True)) - L.RIDGE).abs().max()); print(out, flush=True)
for k, kw in (("A weekly refit", dict(freq="W-MON")), ("B alpha ensemble", dict(alphas=(3.0, 10.0, 30.0, 100.0)))):
    L.judge(k + " v8.4", L.perp(walk(DV, True, **kw)), out, dev_start="2021-01-01", replace_ridge=True)
    F.judge(k + " bf2.2", F.cfd(walk(DB, False, **kw)), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen305.json", "w"), indent=1)
