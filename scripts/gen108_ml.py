"""Gen108 (config/gen108_protocol.json): walk-forward ML on BTC/ETH daily returns. Writes results/gen108.csv, results/gen108_preds.parquet."""
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
FEATS = [x for x in D.columns if x not in ("day", "target", "coin")]
print("rows", len(D), "features", FEATS, flush=True)
PRED = {}
for name, make in (("ridge", lambda: Ridge(alpha=10.0)),
                   ("gbm", lambda: HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=50, random_state=0))):
    out = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        if len(te) == 0:
            continue
        mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
        Xtr = ((tr[FEATS] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[FEATS] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = make().fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        out.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    PRED[name] = out
    print(name, "done", flush=True)
D["ridge"], D["gbm"] = PRED["ridge"], PRED["gbm"]
D[["day", "coin", "target", "ridge", "gbm"]].to_parquet(ROOT / "results/gen108_preds.parquet")
b0, H0 = book(pos); k0 = per(b0, "2022-01-01"); B0 = sh(b0, "2022-01-01", "2026-09-30")
res = []
for name, lab in (("ridge", "ML1 ridge (PRIMARY)"), ("gbm", "ML2 gradient boosting (PRIMARY)")):
    w = D.pivot(index="day", columns="coin", values=name).reindex(days).fillna(0.0) * 0.5
    w = w.reindex(columns=CB.CFD).fillna(0.0)
    p = CB.d2h(w, IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)])))
    h = sleeve(p); s = (sh(h, "2021-01-01", "2022-12-31"), sh(h, "2023-01-01", "2024-12-31"), sh(h, "2025-01-01", "2026-09-30"))
    ph = CS.portfolio_v5(pd.concat([H0, h.rename(lab)], axis=1).fillna(0.0))[0]; k1 = per(ph, "2022-01-01"); bA = sh(ph, "2022-01-01", "2026-09-30")
    hit = float((np.sign(D[name]) == np.sign(D["target"]))[D[name].notna() & (D[name] != 0)].mean())
    r = {"test": lab, "DEV 2021-22": s[0], "TEST": s[1], "HOLD": s[2], "hit rate": hit, "corr C*": float(pd.concat([H0["C*"], h], axis=1).groupby(IDX.floor("D")).sum().loc["2021":].corr().iloc[0, 1]),
         "book before": B0, "book after": bA, "book TEST/HOLD before": np.round(k0[1:], 3).tolist(), "book TEST/HOLD after": np.round(k1[1:], 3).tolist()}
    r["pass"] = bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and bA > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    res.append(r); print({kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in r.items()}, flush=True)
pd.DataFrame(res).to_csv(ROOT / "results/gen108.csv", index=False)
print("done", flush=True)
