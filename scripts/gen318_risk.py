"""Gen318 (config/gen318_protocol.json): nested prop risk settings for v8.5 and bf2.4. Writes results/gen318.json."""
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
BF = PF.PRESETS["BrightFunded Two-Step Classic $200k"]; BF = replace(BF, fee=BF.fee + 96.0)
BOOKS = {"v8.5": ("v85", PF.PRESETS["HyroTrader Two-Step $200k"]), "bf2.4": ("bf24", BF)}


def run(h, f, sc, sf, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * sc, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * sf, 0.5 * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "days_to_funded": pb["days_to_funded_median"]}


out = {}
for bn, (f_, firm) in BOOKS.items():
    h = pd.read_parquet(ROOT / f"results/cache_{f_}_final.parquet")["portfolio"].loc["2022-01-01":"2026-09-30 23:00"]
    dd = h.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum(); h = h * 0.15 / (dd.std() * np.sqrt(365))
    rows = [{"sc": sc, "sf": sf, **run(h, firm, sc, sf, "2022-01-01", "2024-12-31 23:00")} for sc, sf in itertools.product((1.5, 2.0, 2.5, 3.0), (1.0, 1.5, 2.0))]
    T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; r = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
    ch = run(h, firm, float(r.sc), float(r.sf), "2025-01-01", "2026-09-30 23:00"); cur = run(h, firm, 2.0, 1.5, "2025-01-01", "2026-09-30 23:00")
    adopt = bool((r.sc, r.sf) != (2.0, 1.5) and ch["net"] > cur["net"] and ch["P_profit"] >= cur["P_profit"] - 0.02 and ch["p10"] >= cur["p10"])
    out[bn] = {"grid 2022-24": rows, "chosen": [float(r.sc), float(r.sf)], "2025-26 chosen": ch, "2025-26 current 2.0/1.5": cur, "adopt": adopt}
    print(bn, out[bn]["chosen"], ch, cur, adopt, flush=True)
json.dump(out, open(ROOT / "results/gen318.json", "w"), indent=1, default=float)
