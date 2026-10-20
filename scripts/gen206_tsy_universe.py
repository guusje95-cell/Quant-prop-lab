"""Gen206 (config/gen206_protocol.json): A3 / F3 on ZN+ZB only. Writes results/gen206.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0]
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(src, g)
F, S, TUNE, JUDGE = g["F"], g["S"], g["TUNE"], g["JUDGE"]
import fbook as B
P140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]
sA = src.replace('MR = ["ZT", "ZF", "ZN", "ZB"]', 'MR = ["ZN", "ZB"]; a = a[a.root.isin(MR)]'); hA = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(sA, hA)
sF = src.replace('B3 = ["ZN", "ZB", "ZF"]', 'B3 = ["ZN", "ZB"]').replace("* 3 * 0.003", "* 2 * 0.0045"); hF = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(sF, hF)
pa = P140["A3"]["params"]; pf = P140["F3"]["params"]
V = {"A3": {"cur": g["a3"](**pa), "long": hA["a3"](**pa)}, "F3": {"cur": g["f3"](**pf), "long": hF["f3"](**pf)}}
rep, repl = {}, {}
for n, v in V.items():
    t = {k: round(S(p, TUNE), 3) for k, p in v.items()}; rep[n] = t; print(n, t, flush=True)
    if t["long"] > t["cur"]:
        repl[n] = v["long"]
out = {"tune": rep, "replaced": list(repl)}
if repl:
    out.update(B.judge(repl, "gen206"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen206.json", "w"), indent=1)
