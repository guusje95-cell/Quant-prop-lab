"""Gen205 (config/gen205_protocol.json): P1 on ES+NQ vs four indices. Writes results/gen205.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0]
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(src, g)
s2 = src.replace('EQ = ["ES", "NQ", "RTY", "YM"]', 'EQ = ["ES", "NQ"]').replace("0.25, np.where", "0.5, np.where")
h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(s2, h)
F, S, TUNE, JUDGE = g["F"], g["S"], g["TUNE"], g["JUDGE"]
import fbook as B
V = {"ALL4": g["p1"](0.3, 0.7, True), "ESNQ": h["p1"](0.3, 0.7, True)}
res = {k: round(S(p, TUNE), 3) for k, p in V.items()}; print(res, "current check", round(S(B.sleeves()["P1"], TUNE), 3))
ch = max(res, key=res.get); out = {"tune": res, "chosen": ch}
if ch == "ESNQ":
    out.update(B.judge({"P1": V["ESNQ"]}, "gen205"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen205.json", "w"), indent=1)
