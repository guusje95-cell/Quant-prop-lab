"""Gen391b (descriptive robustness of the Gen391 candidate): leave-one-member-out and calendar years. Writes results/gen391b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, dd, shp, per, unit, END, CS, base = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "CS", "base"))
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
kept = [s[0] for s in json.loads((ROOT / "results/gen391.json").read_text())["steps (member, basket 2022-24 Sharpe)"]]
def book(keys):
    D24 = pd.DataFrame({k: dd(POOL[k]) for k in keys}).loc["2022":"2024"]; sdv = D24.std()
    bh = sum(POOL[k] / sdv[k] for k in keys); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
    return bh, unit(CS.portfolio_v5(base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0])
bh, b = book(kept); d = dd(bh).loc["2022":END]
out = {"basket by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)}, "book": [shp(b), per(b)], "leave one out (book 2022-26 [periods])": {}}
for k in kept:
    _, bb = book([x for x in kept if x != k]); out["leave one out (book 2022-26 [periods])"][k] = [shp(bb), per(bb)]
(ROOT / "results/gen391b.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
