"""Gen414 (config/gen414_protocol.json): watchlist re-tests vs v9.5. Writes results/gen414.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import ridge_live as RL
import basket_live as BL
from qpl.lab import binance_pack as B
END = "2026-09-30"; days = pd.date_range("2020-01-01", END)
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95)); print("ref", REF, flush=True)
# A
D = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).drop(columns=["y", "ridge"])
def positioning(c):
    d = B.metrics(c).resample("1D").last()
    f = pd.DataFrame({"ltop": np.log(d["sum_toptrader_long_short_ratio"].where(lambda x: x > 0)), "lacc": np.log(d["count_long_short_ratio"].where(lambda x: x > 0))})
    f["dtop7"] = f["ltop"].diff(7); return f
cols = {}
for c in RL.COINS:
    f = positioning(c).reindex(days); m = D["coin"] == c
    for k in f.columns:
        cols.setdefault(k, pd.Series(np.nan, index=D.index)); cols[k][m] = D.loc[m, "day"].map(f[k]).to_numpy()
D = D.assign(**cols); D["y"] = D["target"] / D["vol30"].replace(0, np.nan)
feats = [x for x in D.columns if x not in ("day", "target", "coin", "y")]; pred = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["y"]); te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["y"]); s = np.std(mdl.predict(Xtr)) or 1.0; pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
W = D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
ridgeA = CS._from_daily_weights(W, list(W.columns), 5).reindex(V.index).fillna(0.0)
# B
def last_friday(y, m):
    d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0); return d - pd.Timedelta(days=(d.weekday() - 4) % 7)
def cme():
    W = pd.DataFrame(0.0, index=BL.DAYS, columns=["BTC", "ETH"])
    for c in ("BTC", "ETH"):
        d = pd.read_parquet(ROOT / f"research_data/databento/{c}_1h.parquet"); d = d[d["symbol"] == f"{c}.v.0"].copy()
        d.index = pd.DatetimeIndex(d["ts_event"]).tz_convert("UTC").tz_localize(None); f = d["close"].astype(float); f = f[~f.index.duplicated()]
        s = pd.read_parquet(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"]; s.index = pd.DatetimeIndex(s.index)
        j = pd.concat([f.rename("F"), s.rename("S")], axis=1).dropna(); j = j.groupby(j.index.floor("D")).last().loc[:END]
        exp = pd.Series([last_friday(t.year, t.month) for t in j.index], index=j.index)
        nxt = pd.Series([last_friday((t + pd.offsets.MonthBegin(1)).year, (t + pd.offsets.MonthBegin(1)).month) for t in j.index], index=j.index)
        exp = exp.where(j.index < exp, nxt); dte = (exp - j.index.to_series()).dt.days.clip(lower=3)
        b = (j["F"] / j["S"] - 1) * 365 / dte; z = ((b - b.rolling(90, min_periods=60).mean()) / b.rolling(90, min_periods=60).std()).reindex(BL.DAYS)
        W[c] = np.where(z > 1, 0.25, np.where(z < -1, -0.25, 0.0))
    return W
bk0, _ = BL.basket(V.index); chk = float((bk0 - V["diversifier basket"]).abs().max())
BL.BUILD["CME basis level"] = cme; BL.MEMBERS = BL.MEMBERS + ["CME basis level"]; bkB, _ = BL.basket(V.index)
T = {"A ridge + positioning": (V.assign(**{"ridge ML": ridgeA}), ridgeA), "B basket + CME basis": (V.assign(**{"diversifier basket": bkB}), bkB)}
out = {"reference v9.5": [REF[0], REF[1]], "check basket rebuild max diff": chk, "trials": {}}
for k, (VV, s) in T.items():
    b = unit(CS.portfolio_v5(VV)[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen414.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
