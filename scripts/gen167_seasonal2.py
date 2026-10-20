"""Gen167 (config/gen167_protocol.json): harvest pressure and gasoline grade switch. Writes results/gen167.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))


def seasonal(legs, md0, md1):
    m = list(legs); R = pd.DataFrame({r: D[r].r for r in m}).sort_index(); R = R[R.index.weekday < 5]
    v = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
    md = R.index.month * 100 + R.index.day; on = pd.Series(((md >= md0) & (md <= md1)).astype(float), index=R.index)
    W = pd.DataFrame({r: sgn * on * 0.05 / v[r] for r, sgn in legs.items()})
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), m)


FAM = {"HV": seasonal({"ZC": -1, "ZS": -1}, 701, 930), "GS": seasonal({"RB": -1, "CL": 1}, 901, 1031)}
rep, enter = {}, {}
for n, p in FAM.items():
    s = S(p, TUNE); rep[n] = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
    print(n, rep[n], flush=True)
    if s > 0.3:
        enter[n] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen167_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen167.json", "w"), indent=1)
