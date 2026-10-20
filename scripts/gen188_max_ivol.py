"""Gen188 (config/gen188_protocol.json): commodity MAX and idiosyncratic-vol cross-sections. Writes results/gen188.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen143_families.py")}; exec(open(ROOT / "scripts/gen143_families.py").read().split("R2 = pd.DataFrame")[0], g)
F, S, TUNE, JUDGE, build, R24, xs, COM = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build", "R24", "xs", "COM"))
RC = R24[COM]
MAX = RC.rolling(21, min_periods=18).max()
mkt = RC.mean(axis=1)


def ivol(win=63):
    cov = RC.rolling(win, min_periods=50).cov(mkt); var = mkt.rolling(win, min_periods=50).var()
    beta = cov.div(var, axis=0); res = RC.sub(beta.mul(mkt, axis=0))            # residual with rolling beta (fit window ends today)
    return res.rolling(win, min_periods=50).std()


IV = ivol()
FAM = {"MX": [(lambda n: xs(MAX, COM, n, high_long=False), {"n": n}) for n in (3, 4)],
       "IV": [(lambda n: xs(IV, COM, n, high_long=False), {"n": n}) for n in (3, 4)]}
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
    b = build(base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.137)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen188_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen188.json", "w"), indent=1)
