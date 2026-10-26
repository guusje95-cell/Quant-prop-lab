"""Gen463 (config/gen463_protocol.json): follow-froth as its own sleeve in v9.7. Writes results/gen463.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen440_follow_froth.py").read().split("\nls, _, _ = LL.pnl(idx)")[0]
g = {"__file__": str(ROOT / "scripts/gen440_follow_froth.py")}; exec(compile(src, "g440", "exec"), g)
CS, LL, V, idx, unit, shp, per, mem_pnl, zser = (g[k] for k in ("CS", "LL", "V", "idx", "unit", "shp", "per", "mem_pnl", "zser"))
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
s = mem_pnl(zser()); b = unit(CS.portfolio_v5(V7.assign(**{"follow froth": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "sleeve": per(s), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen463.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
