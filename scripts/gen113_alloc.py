"""Gen113 (config/gen113_protocol.json): sleeve allocation variants for the v6 and bf books. Writes results/gen113.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, H6, per, sh = (g[k] for k in ("CS", "H6", "per", "sh"))
f = {"__file__": str(ROOT / "scripts/gen106_intraday.py")}
exec(open(ROOT / "scripts/gen106_intraday.py").read().split("\nb0, H0 = book(pos); k0")[0], f)
book, pos = f["book"], f["pos"]
P1 = CS.v5_weights


def erc(S):
    n = len(S); x = np.ones(n) / n
    for _ in range(500):                                  # fixed-point iteration for equal risk contributions
        rc = x * (S @ x); x_new = x * (rc.mean() / rc) ** 0.5; x_new /= x_new.sum()
        if np.abs(x_new - x).max() < 1e-10:
            break
        x = x_new
    return x


def minvar(S):
    n = len(S); r = minimize(lambda x: x @ S @ x, np.ones(n) / n, bounds=[(0, 1)] * n, constraints=({"type": "eq", "fun": lambda x: x.sum() - 1},), method="SLSQP")
    return r.x


def make(kind):
    def wfun(D, sleeves, weiss_scale=0.5):
        W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
        for m in D.index[~D.index.to_period("M").duplicated()]:
            hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
            live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and hist[c].std() > 0]
            if len(live) < 2:
                continue
            X = hist[live]
            if kind in ("erc", "mv"):
                S = LedoitWolf().fit(X.to_numpy()).covariance_
                w = pd.Series((erc if kind == "erc" else minvar)(S), index=live)
            elif kind == "iv90":
                w = 0.10 / X.loc[m - pd.Timedelta(days=90):].std() / len(live)
            else:
                w = 0.10 / X.std() / len(live)
                s = (X.mean() / X.std() * np.sqrt(365)).clip(0, 3)
                if s.sum() > 0:
                    w = w * (0.5 + 0.5 * s / s.mean())
            if "Weiss expiry" in w:
                w["Weiss expiry"] *= weiss_scale
            W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
        return W.ffill().fillna(0.0)
    return wfun


def run(label):
    v = CS.portfolio_v5(H6)[0]; b = book(pos)[0]
    return {"variant": label, "v6 2022-26": sh(v, "2022-01-01", "2026-09-30"), "v6 DEV/TEST/HOLD": per(v, "2022-01-01"),
            "bf 2022-26": sh(b, "2022-01-01", "2026-09-30"), "bf DEV/TEST/HOLD": per(b, "2022-01-01")}


rows = [run("P1 baseline")]
for lab, kind in (("A1 ERC", "erc"), ("A2 min-variance", "mv"), ("A3 inverse-vol 90d", "iv90"), ("A4 half Sharpe tilt", "tilt")):
    CS.v5_weights = make(kind); rows.append(run(lab)); CS.v5_weights = P1
b0 = rows[0]
for r in rows:
    for k in ("v6", "bf"):
        r[f"pass {k}"] = bool(r[f"{k} 2022-26"] > b0[f"{k} 2022-26"] and r[f"{k} DEV/TEST/HOLD"][1] >= b0[f"{k} DEV/TEST/HOLD"][1] and r[f"{k} DEV/TEST/HOLD"][2] >= b0[f"{k} DEV/TEST/HOLD"][2])
    print({k: (np.round(v, 3).tolist() if isinstance(v, tuple) else round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen113.csv", index=False)
