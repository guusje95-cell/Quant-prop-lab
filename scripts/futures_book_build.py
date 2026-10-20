"""Single source of truth for the current futures book: rebuilds all 15 sleeves from their adopted settings (Gen140/143/155/163/166/203,
Gen205 P1 on ES+NQ executed at 16:00 ET, Gen221 sleeve vol targeting), EQR fit 2010-22, 10% vol target.
Env: QPL_DAILY_FLAT=1 -> every held position also pays one round trip per day (firms that flatten at 16:10 ET; reopen at 18:00).
Usage: python scripts/futures_book_build.py [--check]"""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B


def ns(script, cut):
    g = {"__file__": str(ROOT / "scripts" / script)}; exec(open(ROOT / "scripts" / script).read().split(cut)[0], g); return g


g140 = ns("gen140_optimise.py", "GRID = {")
P140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]
prm = lambda k: {kk: (tuple(v) if isinstance(v, list) else v) for kk, v in P140[k]["params"].items()}
S = {"F3": g140["f3"](**prm("F3")), "F5": g140["f5"](**prm("F5")), "G1": g140["g1"](**prm("G1")), "A3": g140["a3"](**prm("A3"))}
S["P1"] = ns("p1_exec_check.py", "\ncur = B.sleeves()")["snap"](16)
g143 = ns("gen143_families.py", "c = {\"__file__\"")
S["U5"] = g143["u5"](252, 6); S["K3"] = g143["k3"](5)
S["R1"] = ns("gen155_r1_refine.py", "if __name__")["r1v"](4, "lowvol", 24)
S.update(ns("gen203_universe.py", "\nres = {}")["sleeves"]("ESNQ"))
S["BC"] = ns("gen163_bigmove.py", "\nFAM = {")["sleeve"](["ZF", "ZN", "ZB"], 2.0, 3)
S["SH"] = ns("gen166_energy_seasonal.py", "\nFAM = {")["spread"]("HO", 801, 1031)
P = pd.DataFrame(S); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
for c in ("F5", "G1", "A3", "U5"):
    sd = P[c].rolling(60, min_periods=40).std().shift(1); P[c] = P[c] * (P[c].loc[:"2022-12-31"].std() / sd).clip(upper=2).fillna(1.0)
b = B.build(P)
tag = "_dailyflat" if os.environ.get("QPL_DAILY_FLAT") == "1" else ""
out = {"daily flat": bool(tag), "book 2010-17 / 2018-22 / 2023-26": [round(F.sharpe(b, *s), 3) for s in F.SPLITS],
       "sleeves 2023-26": {c: round(F.sharpe(P[c], *B.JUDGE), 2) for c in P.columns}}
if "--check" in sys.argv:
    ref = B.sleeves(); out["max abs diff vs saved sleeves"] = {c: float((P[c] - ref[c].reindex(P.index).fillna(0.0)).abs().max()) for c in P.columns}
print(json.dumps(out, indent=1))
P.to_parquet(ROOT / f"results/futures_book_rebuild_sleeves{tag}.parquet"); b.to_frame("book").to_parquet(ROOT / f"results/futures_book_rebuild{tag}.parquet")
