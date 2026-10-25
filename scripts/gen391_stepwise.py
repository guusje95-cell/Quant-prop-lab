"""Gen391 (config/gen391_protocol.json, flagged). Writes results/gen391.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("ref_book = pd.read_parquet")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, idx, dd, shp, per, unit, END, CS, base, K1 = (g[k] for k in ("POOL", "idx", "dd", "shp", "per", "unit", "END", "CS", "base", "K1"))
ref_book = pd.read_parquet(ROOT / "results/gen385_book_hourly.parquet")["book"]; REF = (shp(ref_book), per(ref_book))
D = pd.DataFrame({k: dd(v) for k, v in POOL.items()}).loc["2022":END].fillna(0.0); D24 = D.loc[:"2024"]
K1d = dd(K1).loc["2022":"2024"]
cand = [k for k in D if abs(float(pd.concat([D24[k], K1d], axis=1).corr().iloc[0, 1])) < 0.3 and D24[k].std() > 0]
def bsr(keys):
    x = (D24[keys] / D24[keys].std()).sum(axis=1); return float(x.mean() / x.std() * np.sqrt(365))
kept, cur, steps = [], -9.0, []
while True:
    best = max(((k, bsr(kept + [k])) for k in cand if k not in kept), key=lambda t: t[1], default=(None, -9))
    if best[0] is None or best[1] < cur + 0.05:
        break
    kept.append(best[0]); cur = best[1]; steps.append([best[0], round(cur, 3)])
sdv = D24[kept].std(); bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
d = dd(b).loc["2022":END]
out = {"reference v9.2": [REF[0], REF[1]], "pool size": len(POOL), "candidates (corr filter)": len(cand), "steps (member, basket 2022-24 Sharpe)": steps,
       "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh), "book": [B1, k], "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen391_basket_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen391_book_hourly.parquet")
(ROOT / "results/gen391.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
