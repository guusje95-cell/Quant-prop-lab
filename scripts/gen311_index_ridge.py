"""Gen311 (config/gen311_protocol.json): index ridge ML sleeve on US100/US500/US30 CFDs in bf2.3. Writes results/gen311.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import bf2lab as F
import index_sleeve as IS
END = F.END; IDX = ("US100", "US500", "US30")
vix = pd.read_parquet(F.ROOT / "data/raw/yahoo/VIX.parquet")["close"]; vix.index = pd.DatetimeIndex(vix.index).normalize()


def daily(s):
    x = IS.hourly(s); et = x.index.tz_localize("UTC").tz_convert("America/New_York"); d = pd.Series(pd.DatetimeIndex(et.date), index=x.index)
    wk = et.weekday < 5; snap = wk & (et.hour == 15); rth = wk & (et.hour >= 9) & (et.hour <= 15)
    c = x.close[snap].groupby(d[snap]).last(); hi = x.high[rth].groupby(d[rth]).max().reindex(c.index); lo = x.low[rth].groupby(d[rth]).min().reindex(c.index)
    return c, hi, lo


rows = []; C = {}
for s in IDX:
    c, hi, lo = daily(s); C[s] = (c, hi, lo); r = c.pct_change()
    f = pd.DataFrame(index=c.index)
    for n in (1, 5, 20):
        f[f"r{n}"] = c / c.shift(n) - 1
    f["vol20"] = r.rolling(20).std(); f["ibs"] = ((c - lo) / (hi - lo)).where(hi > lo); f["ma200"] = c / c.rolling(200, min_periods=120).mean() - 1
    f["rsi2"] = IS.rsi2(c); f["target"] = r.shift(-1); f["idx"] = s
    for k in IDX:
        f["is_" + k] = float(s == k)
    rows.append(f)
D = pd.concat(rows).reset_index().rename(columns={"index": "day"}); D["day"] = pd.DatetimeIndex(D["day"])
spx = C["US500"][0].pct_change(); rv = (spx ** 2).rolling(21).sum() * 1e4
vl = vix.shift(1); vrp = (vix ** 2 / 12).reindex(rv.index).shift(1) - rv.shift(1)
D["vix"] = D["day"].map(vl.reindex(pd.DatetimeIndex(sorted(set(D["day"])))).ffill()); D["dvix"] = D["day"].map(vix.diff().shift(1))
D["vrp"] = D["day"].map(vrp)
D["y"] = D["target"] / D["vol20"].replace(0, np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "idx", "y")]
pred = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2019-01-01", END, freq="MS"):
    tr = D[D["day"] < m - pd.Timedelta(days=1)].dropna(subset=["y"]); te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    if len(te) == 0 or len(tr) < 200:
        continue
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s_ = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s_, -1, 1)
D["p"] = pred * 0.5
idx = F.IDXbf; pnl = 0.0; turn = {}
for s in IDX:
    ps = D[D.idx == s].set_index("day")["p"]
    x = IS.hourly(s); r = x.close.reindex(idx).ffill(limit=72).pct_change().fillna(0.0)
    w = IS._event_leg(x, idx, 15, lambda c, hi, lo: ps.reindex(c.index).fillna(0.0))
    pnl = pnl + w * r - w.diff().abs().fillna(0.0) * IS.COST; turn[s] = float(w.diff().abs().sum())
out = {"reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "turnover": turn,
       "corr with the index sleeve (daily)": float(pd.concat([pnl.groupby(pnl.index.floor("D")).sum(), F.IS0.groupby(F.IS0.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1])}
F.judge("index ridge", pnl.rename("index ridge"), out, dev_start="2020-01-01")
json.dump(out, open(F.ROOT / "results/gen311.json", "w"), indent=1)
print(out)
