"""Gen304 (config/gen304_protocol.json): v8.4 / bf2.2 ridge + positioning (A), realised moments (B), US500 spillover (C). Writes results/gen304.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from qpl.lab import binance_pack as B
import ridge_live as RL
import index_sleeve as IS
import v7lab as L
import bf2lab as F
END = L.END
days = pd.date_range("2020-01-01", END)


def walk(D, volscale):
    D = D.copy(); D["y"] = D["target"] / D["vol30"].replace(0, np.nan) if volscale else D["target"]
    feats = [x for x in D.columns if x not in ("day", "target", "coin", "y", "ridge")]; pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5


def per_coin(D, fn):
    cols = {}
    for c in RL.COINS:
        f = fn(c).reindex(days); m = D["coin"] == c
        for k in f.columns:
            cols.setdefault(k, pd.Series(np.nan, index=D.index)); cols[k][m] = D.loc[m, "day"].map(f[k]).to_numpy()
    return D.assign(**cols)


def positioning(c):
    m = B.metrics(c); d = m.resample("1D").last()
    f = pd.DataFrame({"ltop": np.log(d["sum_toptrader_long_short_ratio"].where(lambda x: x > 0)),
                      "lacc": np.log(d["count_long_short_ratio"].where(lambda x: x > 0))})
    f["dtop7"] = f["ltop"].diff(7); return f


def moments(c):
    k = B.k5(c).loc[:END + " 23:55"]; r = np.log(k.close).diff()
    g = r.groupby(r.index.floor("D"))
    f = pd.DataFrame({"rskew": g.skew(), "dshare": g.apply(lambda x: (x[x < 0] ** 2).sum() / (x ** 2).sum() if (x ** 2).sum() > 0 else np.nan)})
    f["rskew7"] = f["rskew"].rolling(7).mean(); f["dshare"] = f["dshare"].rolling(7).mean(); return f


us = IS.hourly("US500")["close"]; usd = us.groupby(us.index.floor("D")).last(); ur = usd.pct_change()
USF = pd.DataFrame({"us1": ur.reindex(days).fillna(0.0), "usvol": ur.rolling(20).std().reindex(days).ffill()})
ADD = {"A positioning": lambda D: per_coin(D, positioning), "B realised moments": lambda D: per_coin(D, moments),
       "C US500 spillover": lambda D: D.assign(us1=D["day"].map(USF["us1"]), usvol=D["day"].map(USF["usvol"]))}

out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
DV = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).drop(columns=["y"])
DB = RL.predictions(END, spot=True, vrp=True, cal=True).drop(columns=["y"])
out["check v8.4 ridge"] = float((L.perp(walk(DV, True)) - L.RIDGE).abs().max())
out["check bf2.2 ridge"] = float((F.cfd(walk(DB, False)) - F.HB_RIDGE).abs().max()); print(out, flush=True)
for k, fn in ADD.items():
    L.judge(k + " v8.4", L.perp(walk(fn(DV), True)), out, dev_start="2021-01-01", replace_ridge=True)
    F.judge(k + " bf2.2", F.cfd(walk(fn(DB), False)), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen304.json", "w"), indent=1)
