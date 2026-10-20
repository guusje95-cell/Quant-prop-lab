"""Gen184 (config/gen184_protocol.json): copper -> stocks, commodity currencies -> commodities. Writes results/gen184.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen159_fomc_cycle.py")}; exec(open(ROOT / "scripts/gen159_fomc_cycle.py").read().split("FAM = {")[0], c)
F, S, TUNE, JUDGE, h, IX, EQ, D, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "IX", "EQ", "D", "daily_book"))
PX = lambda r: (1 + D[r].r.reindex(IX).fillna(0.0)).cumprod()
ME = IX.to_series().groupby(IX.to_period("M")).max()
COMB = ["GC", "SI", "HG", "CL", "HO", "RB", "ZC", "ZS", "ZW"]
RC = pd.DataFrame({r: D[r].r for r in COMB}).reindex(IX); VC = (RC.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)


def monthly(sig, rule):
    pos = pd.Series(np.nan, index=IX)
    for d in ME:
        v = sig.loc[d]; pos.loc[d] = rule(v) if np.isfinite(v) else 0.0
    return pos.ffill().shift(1).fillna(0.0)


def cu(L):
    p = monthly(np.sign(PX("HG") / PX("HG").shift(L) - 1), lambda v: 1.0 if v < 0 else 0.0)
    return daily_book(pd.DataFrame({r: 0.25 * p for r in EQ}), EQ)


def fxc(mode, L):
    s = np.sign(((PX("6A") / PX("6A").shift(L) - 1) + (PX("6C") / PX("6C").shift(L) - 1)) / 2)
    p = monthly(s, (lambda v: v) if mode == "LS" else (lambda v: 1.0 if v > 0 else 0.0))
    W = (0.10 / VC / len(COMB)).mul(p, axis=0)
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), COMB)


FAM = {"CU": [(cu, {"L": L}) for L in (21, 63)], "FXC": [(fxc, {"mode": m, "L": L}) for m in ("LS", "LO") for L in (21, 63)]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.137)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen184_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen184.json", "w"), indent=1)
