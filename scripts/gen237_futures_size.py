"""Gen237 (config/gen237_protocol.json): futures book at 50k / 100k / 150k MFFU-type accounts. Writes results/gen237.json."""
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
FIRMS = {s: PF.Firm(f"MFFU-type {s // 1000}k (ASSUMED)", s, fee, (0.06,), 0.0, "initial", True, dd, "trailing_lock", False, 2, 0, 0.90, 14, 0.0, False, 0.0, "ASSUMED", payout_min=250)
         for s, fee, dd in ((50_000, 150, 0.04), (100_000, 250, 0.03), (150_000, 350, 0.03))}
b = pd.read_parquet(ROOT / "results/book_corrected_p1.parquet")["book"]; b = b * 0.15 / (b.loc[:"2022-12-31"].std() * np.sqrt(252))


def run(f, sc, sf, a, z, halve=False):
    x = b.loc[a:z]; x = x - 0.5 * x.mean() if halve else x
    d = pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})
    pb = PF.pipeline(d, f, 5, 1, sc, sf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "P_funded": round(pb["P_funded"], 3)}


out = {}
for s, f in FIRMS.items():
    rows = [{"sc": sc, "sf": sf, **run(f, sc, sf, "2010-06-01", "2022-12-31")} for sc, sf in itertools.product((0.33, 0.5, 0.75, 1.0), (0.25, 0.33, 0.5))]
    T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; r = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
    out[f"{s // 1000}k"] = {"chosen": [float(r.sc), float(r.sf)], "net 2010-22": int(r.net), "2023-26": run(f, r.sc, r.sf, "2023-01-01", "2026-09-30"),
                            "half-mean 2023-26": run(f, r.sc, r.sf, "2023-01-01", "2026-09-30", True)}
    print(s, out[f"{s // 1000}k"], flush=True)
out["chosen size (2010-22)"] = max((k for k in out), key=lambda k: out[k]["net 2010-22"])
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen237.json", "w"), indent=1)
