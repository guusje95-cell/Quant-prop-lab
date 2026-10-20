"""New bf (Gen234) with the Gen230 settings vs the old bf: 2025-26 bootstrap (report). Writes results/gen234_prop.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
f = replace(PF.PRESETS["BrightFunded Two-Step Classic $100k"], fee=591.0)
b = pd.read_parquet(ROOT / "results/gen234_book.parquet")["book"].loc["2022-01-01":"2026-09-30 23:00"]
dd = b.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum(); h = b * 0.15 / (dd.std() * np.sqrt(365))
out = {}
for tag, x in (("normal", h), ("half-mean", h - 0.5 * h.mean())):
    x = x.loc["2025-01-01":]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * f.daily_loss), horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    out[tag] = {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen234_prop.json", "w"), indent=1)
