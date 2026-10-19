"""Gen109 X1 checks (descriptive, no selection): ridge alpha, feature groups dropped, per coin, execution delay, 2x costs, quarterly
refit, placebo (predictions shuffled in 30-day blocks). Each variant: sleeve DEV/TEST/HOLD and v6 2022-26. Writes results/gen109_check.csv."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen108_ml.py")}
exec(open(ROOT / "scripts/gen108_ml.py").read().split("PRED = {}")[0], g)
D, FEATS = g["D"], g["FEATS"]
h = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], h)
CS, H6, B0, per, sh = h["CS"], h["H6"], h["B0"], h["per"], h["sh"]
END = "2026-09-30"


def walk(feats, alpha=10.0, step="MS"):
    out = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq=step):
        nxt = m + (pd.offsets.MonthBegin(1) if step == "MS" else pd.offsets.QuarterBegin(1, startingMonth=1))
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= m) & (D["day"] < nxt)]
        if len(te) == 0:
            continue
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=alpha).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        out.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return out


def evaluate(pred, coins=("BTC", "ETH"), lag=0, cost=5, shuffle=None):
    w = pd.DataFrame({"day": D["day"], "coin": D["coin"], "p": pred}).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
    if shuffle is not None:
        w = pd.DataFrame(w.to_numpy()[shuffle], index=w.index, columns=w.columns)
    w = w[[c for c in w.columns if c in coins]]
    hh = CS._from_daily_weights(w, list(w.columns), cost).loc[:END + " 23:00"]
    if lag:
        hh = hh.shift(lag).fillna(0.0)                    # approximate: the whole sleeve P&L stream delayed
    p = per(hh, "2021-01-01"); v = CS.portfolio_v5(pd.concat([H6, hh.rename("ml")], axis=1).fillna(0.0))[0]
    return {"DEV": p[0], "TEST": p[1], "HOLD": p[2], "v6 2022-26": sh(v, "2022-01-01", "2026-09-30")}


base = walk(FEATS)
FLOW = ["zc", "zk"]; DERIV = ["fund1", "fund7", "prem", "oi1", "oi7", "imb"]; PRICE = ["r1", "r3", "r7", "r30", "vol7", "vol30"]
rows = []
for nm, pred, kw in (("base (alpha 10, monthly)", base, {}), ("alpha 1", walk(FEATS, 1.0), {}), ("alpha 100", walk(FEATS, 100.0), {}),
                     ("quarterly refit", walk(FEATS, step="QS"), {}),
                     ("without Coinbase/kimchi z", walk([f for f in FEATS if f not in FLOW]), {}),
                     ("without derivatives features", walk([f for f in FEATS if f not in DERIV]), {}),
                     ("price features only", walk(PRICE + ["is_eth"]), {}),
                     ("BTC only", base, {"coins": ("BTC",)}), ("ETH only", base, {"coins": ("ETH",)}),
                     ("2x costs (10 bp)", base, {"cost": 10}), ("executed 1h late", base, {"lag": 1}), ("executed 6h late", base, {"lag": 6})):
    r = {"variant": nm, **evaluate(pred, **kw)}; rows.append(r); print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
days = sorted(D["day"].unique()); n = len(days); rng = np.random.default_rng(9); sims = []
b = evaluate(base); blocks = np.arange(n) // 30
for _ in range(100):
    order = rng.permutation(blocks.max() + 1); perm = np.concatenate([np.where(blocks == k)[0] for k in order])
    r = evaluate(base, shuffle=perm); sims.append(np.mean([r["TEST"], r["HOLD"]]))
sims = np.array(sims); actual = np.mean([b["TEST"], b["HOLD"]])
rows.append({"variant": "placebo: predictions shuffled in 30-day blocks (100)", "mean TEST/HOLD": float(sims.mean()), "p95": float(np.percentile(sims, 95)),
             "actual": float(actual), "p-value": float((sims >= actual).mean())}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen109_check.csv", index=False)
