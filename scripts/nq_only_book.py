"""Diagnostic (no new trial): the validated equity sleeves restricted to NQ only, EQR-combined (weights fit 2010-22), 10% vol.
R1 at 14:00 ET low-vol sizing (Gen155), P1 IBS long-only 0.3, F5 vol-managed (20d, cap 2), T1, T2, FC, MM, OIL. Writes results/nq_only_book.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
D, daily_book, IX, PX, monthly = c["D"], c["daily_book"], c["IX"], c["PX"], c["monthly"]
k = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], k)
M = k["M"]
r1 = {"__file__": str(ROOT / "scripts/gen155_r1_refine.py")}; src = open(ROOT / "scripts/gen155_r1_refine.py").read().split('if __name__')[0]
src = src.replace('EQ = ["ES", "NQ", "RTY", "YM"]', 'EQ = ["NQ"]'); exec(src, r1)
p1 = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; s1 = open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0]
s1 = s1.replace('EQ = ["ES", "NQ", "RTY", "YM"]', 'EQ = ["NQ"]'); exec(s1, p1)
N = ["NQ"]; RN = D["NQ"].r.reindex(IX)
rv = RN.rolling(20).std() * np.sqrt(252)
sl = {"R1": r1["r1v"](4, "lowvol", 24) * 4,
      "P1": p1["p1"](0.3, 0.7, True) * 4,
      "F5": daily_book(pd.DataFrame({"NQ": (0.15 / rv).clip(upper=2).shift(1).fillna(0.0)}), N)}
for n, m in M.items():
    sl[n] = daily_book(pd.DataFrame({"NQ": m * 1.0}), N)
sl["OIL"] = daily_book(pd.DataFrame({"NQ": monthly(np.sign(PX("CL") / PX("CL").shift(21) - 1), lambda v: 1.0 if v < 0 else 0.0)}), N)
P = pd.DataFrame(sl); b = B.build(P)
out = {"sleeves (tune / 2023-26)": {n: [round(F.sharpe(p, *B.TUNE), 2), round(F.sharpe(p, *B.JUDGE), 2)] for n, p in sl.items()},
       "NQ-only book 2010-17 / 2018-22 / 2023-26": [round(F.sharpe(b, *s), 3) for s in F.SPLITS],
       "NQ buy-and-hold 2023-26": round(F.sharpe(RN.dropna(), *B.JUDGE), 3),
       "2023-26 by year": {str(y): round(F.sharpe(b, f"{y}-01-01", f"{y}-12-31"), 2) for y in range(2023, 2027)}}
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/nq_only_book.json", "w"), indent=1)
b.to_frame("book").to_parquet(ROOT / "results/nq_only_book.parquet")
