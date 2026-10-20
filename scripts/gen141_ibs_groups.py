"""Gen141 (config/gen141_protocol.json): IBS reversal per asset group, nested. Writes results/gen141.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen140_optimise.py").read()
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], g)
D, daily_book, daily_hl, S, TUNE, JUDGE, F = (g[k] for k in ("D", "daily_book", "daily_hl", "S", "TUNE", "JUDGE", "F"))
exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], g)
build = g["build"]
GROUPS = {"rates": ["ZT", "ZF", "ZN", "ZB"], "fx": ["6E", "6J", "6B", "6A", "6C", "6S"], "metals": ["GC", "SI", "HG"],
          "energy": ["CL", "NG", "RB", "HO"], "ags": ["ZC", "ZS", "ZW", "LE", "HE"]}


def ibs_group(members, lo, hi, longonly):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); W = {}
    for r in members:
        h = daily_hl(r); ibs = (h.c - h.lo) / (h.hi - h.lo); ok = (h.ids == 1) & (h.hi > h.lo); sz = 1.0 / len(members)
        W[r] = pd.Series(np.where(ok & (ibs < lo), sz, np.where(ok & (ibs > hi) & (not longonly), -sz, 0.0)), index=h.index)
    return daily_book(pd.DataFrame(W).reindex(R.index).fillna(0.0).shift(1).fillna(0.0), members)


rep, enter = {}, {}
for gname, mem in GROUPS.items():
    res = []
    for (lo, hi) in ((0.1, 0.9), (0.2, 0.8), (0.3, 0.7)):
        for lonly in (False, True):
            p = ibs_group(mem, lo, hi, lonly); res.append((S(p, TUNE), (lo, hi, lonly), p))
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[gname] = {"best": list(prm), "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[f"IBS {gname}"] = p
    print(gname, rep[gname], flush=True)
B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]
base = {}
for k, v in B140.items():
    prm = {kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}
    base[k] = {"F3": g["f3"], "F5": g["f5"], "G1": g["g1"], "P1": g["p1"], "A3": g["a3"]}[k](**prm)
book = build(pd.DataFrame({**base, **enter}), "sharpe-weighted")
out = {"groups": rep, "entered": list(enter), "book 2023-26": round(S(book, JUDGE), 3), "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)],
       "reference Gen140": 0.661}
out["adopt"] = bool(out["book 2023-26"] > 0.661)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen141.json", "w"), indent=1)
book.to_frame("book").to_parquet(ROOT / "results/gen141_book.parquet")
