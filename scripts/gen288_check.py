"""Gen288 checks (descriptive, no re-selection): vol-scaled ridge variants in v8.1. Writes results/gen288_check.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
END = L.END; out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
D0 = RL.features(END); KB = AK.zscores(END + " 23:00").mean(axis=1)


def walk(kb=True, vol="vol30", alpha=10.0):
    D = D0.copy()
    if kb:
        D["kb"] = D["day"].map(KB)
    if vol == "vol7":
        D["y"] = D["target"] / D["vol7"].replace(0, np.nan)
    else:
        D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
    feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=alpha).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5


def run(name, w, cost=5, shift=0):
    h = L.perp(w.shift(shift).fillna(0.0) if shift else w, cost)
    b = L.CS.portfolio_v5(pd.concat([L.H6, h.rename("ridge ML")] + L.ALTK, axis=1).fillna(0.0))[0]
    out[name] = {"sleeve D/T/H": np.round(L.per(h, "2021-01-01"), 3).tolist(), "book": [round(L.sh(b, "2022-01-01", END), 3), np.round(L.per(b, "2022-01-01"), 3).tolist()]}
    print(name, out[name], flush=True)


w = walk(); run("adopted candidate (vol30, kb)", w)
run("without kimchi breadth", walk(kb=False)); run("vol7 scaling", walk(vol="vol7"))
run("alpha 3", walk(alpha=3.0)); run("alpha 30", walk(alpha=30.0))
run("2x costs", w, cost=10); run("entry 1 day late", w, shift=1)
json.dump(out, open(L.ROOT / "results/gen288_check.json", "w"), indent=1)
