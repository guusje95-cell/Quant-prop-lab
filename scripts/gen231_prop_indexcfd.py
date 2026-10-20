"""Gen231 (config/gen231_protocol.json): prop settings for the index-CFD book. Writes results/gen231.json."""
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
f = replace(PF.PRESETS["BrightFunded Two-Step Classic $100k"], fee=591.0)
b = pd.read_parquet(ROOT / "results/gen201_book.parquet")["book"].loc["2022-01-01":"2026-09-30"]
b = b * 0.15 / (b.loc[:"2024-12-31"].std() * np.sqrt(252))


def run(x, sc, sf, a, z, halve=False):
    x = x.loc[a:z]; x = x - 0.5 * x.mean() if halve else x
    d = pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})
    pb = PF.pipeline(d, f, 5, 1, sc, sf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


rows = [{"sc": sc, "sf": sf, **run(b, sc, sf, "2022", "2024")} for sc, sf in itertools.product((0.5, 1.0, 1.5, 2.0), (0.5, 1.0, 1.5))]
T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; ch = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
c = (float(ch.sc), float(ch.sf)); cur = (1.0, 0.5)
out = {"grid 2022-24": rows, "chosen": c, "2025-26 chosen": run(b, *c, "2025", "2026-09-30"), "2025-26 Gen201 (1.0/0.5)": run(b, *cur, "2025", "2026-09-30"),
       "half-mean 2025-26 chosen": run(b, *c, "2025", "2026-09-30", True), "half-mean 2025-26 Gen201": run(b, *cur, "2025", "2026-09-30", True)}
print(json.dumps({k: v for k, v in out.items() if k != "grid 2022-24"}, indent=1)); json.dump(out, open(ROOT / "results/gen231.json", "w"), indent=1)
