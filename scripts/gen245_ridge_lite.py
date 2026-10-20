"""Gen245 (config/gen245_protocol.json): ridge-lite (Binance-only features) as the v7 ML sleeve. Writes results/gen245.json."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen106_intraday.py")}
exec(open(ROOT / "scripts/gen106_intraday.py").read().split("\nb0, H0 = book(pos); k0")[0], g)
CB, B, R, pos, IDX, book, per, sh, sleeve = (g[k] for k in ("CB", "B", "R", "pos", "IDX", "book", "per", "sh", "sleeve"))
import crypto_sleeves as CS
from qpl.lab.data import stablecoin_caps
END = "2026-09-30"; MORE = ROOT / "research_data/more"
days = pd.date_range("2020-01-01", END)
zk = pd.read_parquet(ROOT / "results/gen105_zk_strict.parquet")
caps = stablecoin_caps(); caps = caps.where(caps > 0); caps.index = pd.DatetimeIndex(caps.index).normalize()
stab = (caps / caps.shift(1) - 1).shift(2).reindex(days)
rows = []
for c in ("BTC", "ETH"):
    k = B.k5(c).loc[:END + " 23:55"]
    close = k.close.resample("1D").last().reindex(days); ret = close.pct_change()
    f = pd.DataFrame(index=days)
    for n in (1, 3, 7, 30):
        f[f"r{n}"] = close / close.shift(n) - 1
    f["vol7"] = ret.rolling(7).std(); f["vol30"] = ret.rolling(30).std()
    fu = B.funding(c); fd = fu.groupby((fu.index - pd.Timedelta(seconds=1)).floor("D")).sum().reindex(days)
    f["fund1"] = fd; f["fund7"] = fd.rolling(7).mean()
    pm = B.premium(c)["close"]; f["prem"] = pm.groupby(pm.index.floor("D")).mean().reindex(days)
    oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1D").last().reindex(days)
    f["oi1"] = oi / oi.shift(1) - 1; f["oi7"] = oi / oi.shift(7) - 1
    tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum()
    f["imb"] = ((2 * tb - vv) / vv).reindex(days)
    bn = k.close.resample("1h").last(); cb = CB.coinbase(f"{c}-USD"); prem = (cb / bn - 1).dropna()
    p24 = prem.rolling(24, min_periods=20).mean(); zc = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
    f["zc"] = zc.resample("1D").last().reindex(days)
    f["zk"] = zk.get(f"zk_strict_{c}", pd.Series(dtype=float)).reindex(days)
    dv = pd.read_parquet(ROOT / f"data/raw/deribit/{c}_DVOL.parquet")["close"]; dv.index = pd.DatetimeIndex(dv.index).tz_localize(None).normalize()
    f["dvol1"] = (dv / dv.shift(1) - 1).reindex(days)
    f["stab"] = stab; f["is_eth"] = 1.0 if c == "ETH" else 0.0
    f["target"] = ret.shift(-1); f["coin"] = c
    rows.append(f)
D = pd.concat(rows).reset_index().rename(columns={"index": "day"})
FEATS = [x for x in D.columns if x not in ("day", "target", "coin", "zc", "zk", "dvol1", "stab")]
print("features", FEATS, flush=True)
out = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
    te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    if len(te) == 0:
        continue
    mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
    Xtr = ((tr[FEATS] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[FEATS] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s_ = np.std(mdl.predict(Xtr)) or 1.0
    out.loc[te.index] = np.clip(mdl.predict(Xte) / s_, -1, 1)
D["lite"] = out
D[["day", "coin", "target", "lite"]].to_parquet(ROOT / "results/gen245_preds.parquet")
G = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], G)
H6, perG, shG = G["H6"], G["per"], G["sh"]
def sleeve_from(col, path):
    P = pd.read_parquet(path); w = P.pivot(index="day", columns="coin", values=col).fillna(0.0) * 0.5
    return CS._from_daily_weights(w, ["BTC", "ETH"], 5).loc[:END + " 23:00"]
lite = sleeve_from("lite", ROOT / "results/gen245_preds.parquet"); full = sleeve_from("ridge", ROOT / "results/gen108_preds.parquet")
v6 = CS.portfolio_v5(H6)[0]; B0, k0 = shG(v6, "2022-01-01", "2026-09-30"), perG(v6, "2022-01-01")
vl = CS.portfolio_v5(pd.concat([H6, lite.rename("ridge ML")], axis=1).fillna(0.0))[0]; BL, kL = shG(vl, "2022-01-01", "2026-09-30"), perG(vl, "2022-01-01")
vf = CS.portfolio_v5(pd.concat([H6, full.rename("ridge ML")], axis=1).fillna(0.0))[0]; BF, kF = shG(vf, "2022-01-01", "2026-09-30"), perG(vf, "2022-01-01")
p = perG(lite, "2020-01-01")
import json
outj = {"lite sleeve D/T/H": np.round(p, 3).tolist(), "full ridge sleeve D/T/H": np.round(perG(full, "2020-01-01"), 3).tolist(),
        "v6": [round(B0, 3), np.round(k0, 3).tolist()], "v6 + lite": [round(BL, 3), np.round(kL, 3).tolist()], "v7 (v6 + full)": [round(BF, 3), np.round(kF, 3).tolist()]}
outj["pass"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and BL > B0 and kL[1] >= k0[1] and kL[2] >= k0[2])
outj["use lite for live v7"] = bool(outj["pass"] and BL >= 0.95 * BF)
print(json.dumps(outj)); json.dump(outj, open(ROOT / "results/gen245.json", "w"), indent=1)
