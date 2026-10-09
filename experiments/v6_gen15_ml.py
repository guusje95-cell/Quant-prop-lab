"""V6 gen15 d: ML on the futures instrument panel (ridge vs LightGBM vs simple F7 combo). Protocol config/v6_gen15_protocol.json.
Annual expanding walk-forward; target = vol-normalised return over t+2..t+21; purge 22 days before each refit."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen15_protocol.json"
P = FP.build(); U, utab = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
SIG = PB.sigma(ret)
lp = FF.logp(ret)
sd = ret.ewm(span=35, min_periods=20, ignore_na=True).std()
feat = {}
for L in (21, 63, 126, 252):
    feat[f"ts{L}"] = np.sign(lp - lp.shift(L))
for f_, s_ in ((8, 32), (16, 64), (32, 128), (64, 256)):
    feat[f"ew{f_}"] = ((lp.ewm(span=f_, min_periods=f_).mean() - lp.ewm(span=s_, min_periods=s_).mean()) / sd).clip(-20, 20)
feat["carry"] = FF.carry(ret, cy, 21)
feat["sigma"] = SIG
feat["sig_ratio"] = SIG / SIG.rolling(252, min_periods=126).mean()
feat["skew"] = ret.rolling(126, min_periods=100).skew()
feat["dhi"] = (lp - lp.rolling(252, min_periods=126).max()) / (sd * np.sqrt(252))
feat["dlo"] = (lp - lp.rolling(252, min_periods=126).min()) / (sd * np.sqrt(252))
codes = {c: i for i, c in enumerate(sorted(utab.loc[U, "asset_class"].unique()))}
feat["cls"] = pd.DataFrame({c: codes[utab.loc[c, "asset_class"]] for c in U}, index=ret.index)
fwd = ret.fillna(0).rolling(20).sum().shift(-21) / (SIG / np.sqrt(256) * np.sqrt(20))   # sum r_{t+2..t+21} / (daily sigma*sqrt20)
fwd = fwd.where(ret.notna().cumsum() > 256)
names = list(feat)
stack = pd.concat({k: v.stack(future_stack=True) for k, v in feat.items()}, axis=1)
stack["y"] = fwd.stack(future_stack=True)
stack = stack.replace([np.inf, -np.inf], np.nan)
dates = stack.index.get_level_values(0)
elig = (ret.notna().cumsum() >= 256).stack(future_stack=True).reindex(stack.index).fillna(False).to_numpy()
stack = stack[elig]
dates = stack.index.get_level_values(0)
print("rows", len(stack))
preds = {"RIDGE": pd.Series(np.nan, index=stack.index), "LGBM": pd.Series(np.nan, index=stack.index)}
imp = {}
for Y in range(1995, 2025):
    end = pd.Timestamp(f"{Y - 1}-12-31") - pd.Timedelta(days=32)      # purge: target window must end before the refit
    tr = stack[(dates <= end) & (dates >= pd.Timestamp("1980-01-01"))].dropna()
    tr = tr[tr.index.get_level_values(0).dayofweek == 2]               # ~every 5th day (Wednesdays)
    te_mask = (dates >= pd.Timestamp(f"{Y}-01-01")) & (dates <= pd.Timestamp(f"{Y}-12-31"))
    te = stack[te_mask][names].fillna(0.0)
    Xtr, ytr = tr[names].fillna(0.0), tr["y"].clip(-5, 5)
    sc = StandardScaler().fit(Xtr)
    rg = Ridge(alpha=10.0).fit(sc.transform(Xtr), ytr)
    p_tr = rg.predict(sc.transform(Xtr)); preds["RIDGE"].loc[te.index] = rg.predict(sc.transform(te)) / np.mean(np.abs(p_tr))
    gb = lgb.LGBMRegressor(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=500, colsample_bytree=0.8,
                           random_state=0, verbose=-1).fit(Xtr, ytr)
    p_tr = gb.predict(Xtr); preds["LGBM"].loc[te.index] = gb.predict(te) / np.mean(np.abs(p_tr))
    imp[Y] = dict(zip(names, np.round(gb.feature_importances_ / gb.feature_importances_.sum(), 3)))
    if Y in (1995, 2005, 2013):
        imp[f"ridge_coef_{Y}"] = dict(zip(names, np.round(rg.coef_, 4)))
    print(Y, len(tr), flush=True)
pd.DataFrame(preds).to_parquet(ROOT / "results/v6_gen15_ml_preds.parquet")
combo = ((FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0) + FF.carry(ret, cy, 21).fillna(0)) / 4).where(ret.notna().cumsum() > 0)
out = {}
pn = {}
for k, pser in preds.items():
    sig = pser.unstack().reindex(index=ret.index, columns=U).clip(-1, 1)
    d = PB.run(ret, sig, cost, sig=SIG)
    pn[k] = d["net"]
d7 = PB.run(ret, combo.loc["1995-01-01":].reindex(ret.index), cost, sig=SIG)
pn["F7"] = d7["net"]
OOS, SEC = ("1995-01-01", "2013-12-31"), ("2014-01-01", "2024-03-28")
for k, x in pn.items():
    out[k] = {"OOS": PB.stats(x.loc[OOS[0]:OOS[1]])["sharpe"], "SEC": PB.stats(x.loc[SEC[0]:SEC[1]])["sharpe"],
              "corr_with_F7_OOS": float(x.loc[OOS[0]:OOS[1]].corr(pn["F7"].loc[OOS[0]:OOS[1]]))}
a = pd.concat([pn["LGBM"], pn["RIDGE"], pn["F7"]], axis=1, keys=["L", "R", "F"]).loc[OOS[0]:OOS[1]].dropna().to_numpy()
idx = T.stationary_bootstrap_indices(len(a), 1000, 20, np.random.default_rng(1))
shp = lambda v: v.mean(axis=1) / v.std(axis=1) * 16
for j, k in ((0, "LGBM"), (1, "RIDGE")):
    diff = shp(a[:, j][idx]) - shp(a[:, 2][idx])
    out[k]["P(sharpe<=F7)"] = float(np.mean(diff <= 0))
    out[k]["adopt"] = bool(out[k]["OOS"] >= out["F7"]["OOS"] + 0.10 and out[k]["P(sharpe<=F7)"] < 0.10)
out["LGBM"]["adopt"] = bool(out["LGBM"]["adopt"] and out["LGBM"]["OOS"] > out["RIDGE"]["OOS"])
out["importance"] = imp
(ROOT / "results/v6_gen15_ml.json").write_text(json.dumps(out, indent=1, default=float))
pd.DataFrame(pn).to_parquet(ROOT / "results/v6_gen15_ml_pnl.parquet")
for k in ("RIDGE", "LGBM"):
    hid = f"H15d_{k}"
    v6.record(hid, "futures/ml", k, {}, "WF_OOS_1995_2013", out[k], 15, PROTO, "futures panel")
    F.decide(F.Hypothesis(hid, "futures/ml", "", "", "", "", "", "", PROTO, generation=15), "PROMISING_BUT_UNVALIDATED" if out[k]["adopt"] else "REJECTED",
             f"WF OOS {out[k]['OOS']:.2f} vs F7 {out['F7']['OOS']:.2f}; P(<=F7) {out[k]['P(sharpe<=F7)']:.2f}; contaminated 2014-24 {out[k]['SEC']:.2f}", {"protocol": PROTO})
print(json.dumps({k: out[k] for k in ("RIDGE", "LGBM", "F7")}, indent=1))
print(pd.DataFrame({y: v for y, v in imp.items() if isinstance(y, int)}).T.mean().sort_values(ascending=False).round(3).to_dict())
print(imp.get("ridge_coef_2013"))
