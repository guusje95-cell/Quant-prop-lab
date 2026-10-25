"""Gen385 (config/gen385_protocol.json, flagged post hoc). Writes results/gen385.json and results/gen385_book_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]
g = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(src, "g383", "exec"), g)
CS, base, te, ke, dd, shp, per, unit, REF, END = (g[k] for k in ("CS", "base", "te", "ke", "dd", "shp", "per", "unit", "REF", "END"))
b384 = pd.read_parquet(ROOT / "results/gen384_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": te, "alt kimchi": ke, "diversifier basket": b384}))[0]); r = [shp(b), per(b)]
d = dd(b).loc["2022":END]; eq = (1 + 2 * d).cumprod()
out = {"reference v9.1": [REF[0], REF[1]], "v9.1 + ensembles + Gen384 basket": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3))),
       "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "worst day at risk 2": round(float(2 * d.min()), 4), "max DD at risk 2": round(float((eq / eq.cummax() - 1).min()), 4)}
b.to_frame("book").to_parquet(ROOT / "results/gen385_book_hourly.parquet")
(ROOT / "results/gen385.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
