"""Gen399 (config/gen399_protocol.json, flagged). Writes results/gen399.json and results/gen399_sleeve_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve"))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")
v94 = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": sleeve(C6)}))[0]); REF = (shp(v94), per(v94))
ens = sum(sleeve(C6, win=w) for w in (60, 90, 180)) / 3
b = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": ens}))[0]); r = [shp(b), per(b)]
d = dd(b).loc["2022":END]
out = {"reference v9.4": [REF[0], REF[1]], "ensemble sleeve": per(ens), "book": r, "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
ens.to_frame("relative crowding 6").to_parquet(ROOT / "results/gen399_sleeve_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen399_book_hourly.parquet")
(ROOT / "results/gen399.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
