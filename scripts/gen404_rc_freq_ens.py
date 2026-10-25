"""Gen404 (config/gen404_protocol.json, flagged). Writes results/gen404.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
dd, shp, per, unit, END, CS, V, rc6, a, bsm, REF = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "rc6", "a", "bsm", "REF"))
ens = (rc6 + a + bsm) / 3
b = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": ens}))[0]); r = [shp(b), per(b)]
d = dd(b).loc["2022":END]
out = {"reference v9.4": [REF[0], REF[1]], "sleeve": per(ens), "book": r, "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
ens.to_frame("relative crowding 6").to_parquet(ROOT / "results/gen404_sleeve_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen404_book_hourly.parquet")
(ROOT / "results/gen404.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
