"""Gen294 (config/gen294_protocol.json): Gen263 altcoin ridge with volatility-scaled targets, vs v8.3. Writes results/gen294.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END
days = pd.date_range("2020-01-01", END); ZK = AK.zscores(END + " 23:00")
D0 = RL.features(END); btc = D0[D0["coin"] == "BTC"].set_index("day")[["r1", "zc"]].rename(columns={"r1": "btc_r1", "zc": "btc_zc"})
rows = []
for c in AK.coins():
    k = B.k5(c).loc[:END + " 23:55"]; close = k.close.resample("1D").last().reindex(days); ret = close.pct_change()
    f = pd.DataFrame(index=days)
    for n in (1, 3, 7, 30):
        f[f"r{n}"] = close / close.shift(n) - 1
    f["vol7"] = ret.rolling(7).std(); f["vol30"] = ret.rolling(30).std()
    fu = B.funding(c); fd = fu.groupby((fu.index - pd.Timedelta(seconds=1)).floor("D")).sum().reindex(days); f["fund1"] = fd; f["fund7"] = fd.rolling(7).mean()
    pm = B.premium(c)["close"]; f["prem"] = pm.groupby(pm.index.floor("D")).mean().reindex(days)
    oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1D").last().reindex(days); f["oi1"] = oi / oi.shift(1) - 1; f["oi7"] = oi / oi.shift(7) - 1
    tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum(); f["imb"] = ((2 * tb - vv) / vv).reindex(days)
    f["zk"] = ZK[c]
    cbf = L.ROOT / f"research_data/coinbase/{c}-USD_1h.parquet"
    if cbf.exists():
        cb = pd.read_parquet(cbf)["close"]; cb.index = pd.DatetimeIndex(cb.index); bn = k.close.resample("1h").last(); pr = (cb / bn - 1).dropna()
        p24 = pr.rolling(24, min_periods=20).mean(); f["zc"] = ((p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()).resample("1D").last().reindex(days)
    else:
        f["zc"] = np.nan
    sp = pd.read_parquet(L.ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet").loc[:END + " 23:00"]; sd = sp.groupby(pd.DatetimeIndex(sp.index).floor("D")).sum()
    simb = ((2 * sd["taker_buy_volume"] - sd["volume"]) / sd["volume"]).replace([np.inf, -np.inf], np.nan).reindex(days); f["simb"] = simb; f["sdiv"] = simb - f["imb"]
    f = f.join(btc); f["target"] = ret.shift(-1); f["coin"] = c; rows.append(f)
D = pd.concat(rows).reset_index().rename(columns={"index": "day"}).replace([np.inf, -np.inf], np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "coin")]; pred = pd.Series(np.nan, index=D.index)
D["target"] = D["target"] / D["vol30"].replace(0, np.nan)                 # Gen294: volatility-scaled target
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
    te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    mu, sd_ = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd_).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd_).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
w = D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.1
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
L.judge("pooled altcoin ridge", L.perp(w), out, dev_start="2021-01-01")
json.dump(out, open(L.ROOT / "results/gen294.json", "w"), indent=1)
