"""Gen230 stress: chosen vs current prop settings when the books' mean return is halved (live Sharpe ~ half the backtest). Writes results/gen230_haircut.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen230_prop_crypto.py")}; exec(open(ROOT / "scripts/gen230_prop_crypto.py").read().split("\nout = {}")[0], g)
BOOKS, run = g["BOOKS"], g["run"]
res = json.load(open(ROOT / "results/gen230.json")); out = {}
for n, (hb, f, cur) in BOOKS.items():
    h = hb.loc["2022-01-01":"2026-09-30 23:00"]; dd = h.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    h = h * 0.15 / (dd.std() * np.sqrt(365)); h = h - 0.5 * h.mean()                           # halve the drift
    ch = tuple(res[n]["chosen (2022-24)"])
    out[n] = {"half-Sharpe 2025-26 chosen": run(h, f, *ch, "2025-01-01", "2026-09-30 23:00"), "half-Sharpe 2025-26 current": run(h, f, *cur, "2025-01-01", "2026-09-30 23:00"),
              "half-Sharpe 2025-26 middle 1.5/1.5": run(h, f, 1.5, 1.5, ch[2], "2025-01-01", "2026-09-30 23:00")}
    print(n, out[n], flush=True)
json.dump(out, open(ROOT / "results/gen230_haircut.json", "w"), indent=1)
