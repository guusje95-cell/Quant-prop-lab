"""Gen185 (config/gen185_protocol.json): lagged oil / copper returns predict Treasury futures. Writes results/gen185.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, h, IX, D, daily_book, PX, monthly = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "IX", "D", "daily_book", "PX", "monthly"))
B3 = ["ZF", "ZN", "ZB"]; RB = pd.DataFrame({r: D[r].r for r in B3}).reindex(IX); VB = (RB.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)


def sleeve(root, L):
    p = monthly(np.sign(PX(root) / PX(root).shift(L) - 1), lambda v: -v)
    return daily_book((0.10 / VB / 3).mul(p, axis=0).fillna(0.0).where(np.isfinite, 0.0), B3)


FAM = {"OB": [(sleeve, {"root": "CL", "L": L}) for L in (21, 63)], "CB": [(sleeve, {"root": "HG", "L": L}) for L in (21, 63)]}
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
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen185_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen185.json", "w"), indent=1)
