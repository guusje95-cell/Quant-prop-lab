"""Gen302 (config/gen302_protocol.json): bf2.1 + calendar; ETH-BTC relative-value ridge in v8.3 and bf2.1. Writes results/gen302.json."""
import json
import os
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import ridge_live as RL
import alt_kimchi as AK
import bf2lab as F
END = F.END
BF21 = F.cfd(RL.predictions(END, spot=True, vrp=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5)
F.REF = (F.sh(F.book([], ridge=BF21), "2022-01-01", END), F.per(F.book([], ridge=BF21), "2022-01-01")); F.HB_RIDGE = BF21
out = {"reference bf2.1": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}; print(out, flush=True)


def walk(D, feats, ycol):
    pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=[ycol])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr[ycol]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return pred


# A: bf2.1 + calendar
A = RL.predictions(END, spot=True, vrp=True).drop(columns=["ridge", "y"])
dow = A["day"].dt.dayofweek; A["wkend"] = dow.isin([4, 5]).astype(float); A["mon"] = (dow == 6).astype(float)
fa = [x for x in A.columns if x not in ("day", "target", "coin")]; A["y"] = A["target"]
wa = A.assign(p=walk(A, fa, "y")).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
F.judge("A bf2.1 + calendar", F.cfd(wa), out, dev_start="2021-01-01", replace_ridge=True)

# B/C: relative value ETH - BTC
D = RL.predictions(END, kb=True, vrp=True).drop(columns=["ridge", "y"])
feats = [x for x in D.columns if x not in ("day", "target", "coin", "is_eth", "stab", "kb")]
E, Bt = D[D.coin == "ETH"].set_index("day"), D[D.coin == "BTC"].set_index("day")
R = (E[feats] - Bt[feats]); R["kb"] = E["kb"]; R["stab"] = E["stab"]
spread = (E["target"] - Bt["target"]); sv = spread.shift(1).rolling(30).std()
R["y"] = spread / sv.replace(0, np.nan); R = R.reset_index()
p = walk(R, [x for x in R.columns if x not in ("day", "y")], "y").set_axis(R["day"]) * 0.5
w = pd.DataFrame({"ETH": p, "BTC": -p}).fillna(0.0)
import v7lab as L
L.judge("B relval in v8.3", L.perp(w), out, dev_start="2021-01-01")
F.judge("C relval in bf2.1", F.cfd(w), out, dev_start="2021-01-01")
json.dump(out, open(F.ROOT / "results/gen302.json", "w"), indent=1)
