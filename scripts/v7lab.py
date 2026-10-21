"""Shared harness for v7 entrant tests (perp costs): reference v7 = v6 sleeves + ridge ML, the strict rule, sleeve bars.
    import v7lab as L; L.judge("name", hourly_pnl, out, dev_start="2020-01-01")"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import ridge_live as RL
import os
END = "2026-09-30"
_v = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], _v)
CS, B, H6, sh, per = (_v[k] for k in ("CS", "B", "H6", "sh", "per"))
perp = lambda w, cost=5: CS._from_daily_weights(w, list(w.columns), cost).loc[:END + " 23:00"]
_REF = os.environ.get("QPL_REF", "v8.3")
_KB = _REF in ("v8.1", "v8.2", "v8.3")                                         # v8.1 (Gen268): ridge + kimchi breadth
_VS = _REF in ("v8.2", "v8.3")                                                   # v8.2 (Gen288): volatility-scaled ridge target
RIDGE = perp(RL.predictions(END, kb=_KB, volscale=_VS).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5).rename("ridge ML")
if os.environ.get("QPL_REF", "v8.3") in ("v8", "v8.1", "v8.2", "v8.3"):                     # v8 (Gen247 A adopted): v7 + altcoin kimchi; QPL_REF=v7 for the old base
    import alt_kimchi as AK
    ALTK = [perp(AK.weights(END + " 23:00")).rename("alt kimchi")]
else:
    ALTK = []
if _REF == "v8.3":                                                    # v8.3 (Gen292): inverse-vol premium carry
    H6 = H6.copy(); H6["premium carry"] = CS._from_daily_weights(CS.premium_weights(invvol=True), B.coins(), 5).reindex(H6.index).fillna(0.0)
book = lambda extra: CS.portfolio_v5(pd.concat([H6, RIDGE] + ALTK + list(extra), axis=1).fillna(0.0))[0]
V7 = book([]); REF = (sh(V7, "2022-01-01", END), per(V7, "2022-01-01"))
CST = H6["C*"].groupby(H6.index.floor("D")).sum()


def judge(name, h, out, dev_start="2020-01-01", replace_ridge=False):
    h = h.reindex(H6.index).fillna(0.0)
    s = per(h, dev_start); c = float(pd.concat([CST, h.groupby(h.index.floor("D")).sum()], axis=1).loc[dev_start:].corr().iloc[0, 1])
    if replace_ridge:                                              # the entrant IS a new ridge sleeve: no corr bar
        b = CS.portfolio_v5(pd.concat([H6, h.rename("ridge ML")] + ALTK, axis=1).fillna(0.0))[0]; c = min(c, 0.0)
    else:
        b = book([h.rename(name)])
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01")
    r = {"sleeve D/T/H": np.round(s, 3).tolist(), "corr C*": round(c, 3), "v7": [round(B1, 3), np.round(k1, 3).tolist()]}
    r["pass"] = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and c <= 0.3 and B1 > REF[0] and k1[1] >= REF[1][1] and k1[2] >= REF[1][2])
    out[name] = r; print(name, r, flush=True)
    return r


def xs(score, n=4, size=0.125, min_n=10):
    """Long the n highest, short the n lowest scores (row-wise), size each; zero on days with < min_n scores."""
    rk = score.rank(axis=1, ascending=False); cnt = score.notna().sum(axis=1)
    w = size * rk.le(n).astype(float) - size * rk.gt(cnt - n, axis=0).astype(float)
    return w.mul((cnt >= min_n).astype(float), axis=0).fillna(0.0)
