"""Gen453 (config/gen453_protocol.json): Bybit listings and Weiss full weight against v9.7. Writes results/gen453.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen431_bybit_listings.py").read().split("\nb = unit(CS.portfolio_v5")[0]
g = {"__file__": str(ROOT / "scripts/gen431_bybit_listings.py")}; exec(compile(src, "g431", "exec"), g)
CS, V, ls, s_by, unit, shp, per = (g[k] for k in ("CS", "V", "ls", "s_", "unit", "shp", "per"))
V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
bA = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_by}))[0]); rA = [shp(bA), per(bA)]
orig = CS.v5_weights
CS.v5_weights = lambda D, sleeves=CS.V5_SLEEVES, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)
bB = unit(CS.portfolio_v5(V7)[0]); rB = [shp(bB), per(bB)]
bAB = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_by}))[0]); rAB = [shp(bAB), per(bAB)]
CS.v5_weights = orig
ok = lambda r: bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
out = {"reference v9.7": [REF[0], REF[1]], "A v9.7 + Bybit listings": {"book": rA, "pass": ok(rA)}, "B v9.7 Weiss full weight": {"book": rB, "pass": ok(rB)}}
if ok(rA) and ok(rB):
    out["A + B"] = {"book": rAB, "pass": ok(rAB)}
(ROOT / "results/gen453.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
