"""Gen248 (config/gen248_protocol.json): taker flow by trade size (BTC/ETH perps). Writes results/gen248.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import bf2lab as F
import ridge_live as RL
END = L.END; TS = L.ROOT / "research_data/trade_size"
out = {"reference v7": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
save = lambda: json.dump(out, open(L.ROOT / "results/gen248.json", "w"), indent=1)
days = pd.date_range("2020-01-01", END); feat = {}
for c in ("BTC", "ETH"):
    t = pd.concat([pd.read_parquet(f) for f in sorted(TS.glob(f"{c}USDT_*.parquet"))]).sort_index()
    t.index = pd.DatetimeIndex(t.index); d = t.groupby(t.index.floor("D")).sum().reindex(days)
    bb = d["buy_100k_1m"] + d["buy_ge1m"]; sb = d["sell_100k_1m"] + d["sell_ge1m"]; bs, ss = d["buy_lt10k"], d["sell_lt10k"]
    big = (bb - sb) / (bb + sb); small = (bs - ss) / (bs + ss)
    feat[c] = pd.DataFrame({"imb_big": big, "imb_small": small, "spread": big - small})
# A sleeve
W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    s7 = feat[c]["spread"].rolling(7, min_periods=5).mean(); z = (s7 - s7.rolling(90, min_periods=60).mean()) / s7.rolling(90, min_periods=60).std()
    W[c] = np.where(z > 1, 0.5, np.where(z < -1, -0.5, 0.0))
L.judge("A whale-minus-retail sleeve", L.perp(W), out); F.judge("A whale-minus-retail sleeve", F.cfd(W), out); save()
# B ridge + features
D = RL.features(END)
for c in ("BTC", "ETH"):
    m = D["coin"] == c
    for k in ("imb_big", "imb_small", "spread"):
        D.loc[m, k] = D.loc[m, "day"].map(feat[c][k]).to_numpy()
feats = [x for x in D.columns if x not in ("day", "target", "coin")]; pred = pd.Series(np.nan, index=D.index)
for mo in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < mo - pd.Timedelta(days=1))].dropna(subset=["target"])
    te = D[(D["day"] >= mo) & (D["day"] < mo + pd.offsets.MonthBegin(1))]
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
wp = D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
L.judge("B ridge + trade-size flow", L.perp(wp), out, dev_start="2021-01-01", replace_ridge=True)
F.judge("B ridge + trade-size flow", F.cfd(wp), out, dev_start="2021-01-01", replace_ridge=True); save()
