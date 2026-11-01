"""v9.9 R16c (diagnostic for R16 A, no selection): placebo dates. The same coins and rules, but each event moved by -90 / -60 / -30 /
+30 / +60 / +90 days. If the placebo trades earn as much, R16 is the generic downward drift of new altcoins, not a Coinbase effect.
Writes results/v99/r16c_placebo.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import r16_coinbase as R16

E = R16.events(); idx = pd.date_range("2021-06-01", "2026-12-31 23:00", freq="h"); out = {}
for d in (0, -90, -60, -30, 30, 60, 90):
    ev = {c: t + pd.Timedelta(days=d) for c, t in E.items() if pd.Timestamp("2022-01-01") <= t + pd.Timedelta(days=d) <= pd.Timestamp("2026-09-23")}
    _, used = R16.trades(ev, idx, "A"); R = np.array([u["trade return %"] for u in used])
    out[f"shift {d:+d} days" if d else "actual Coinbase listing"] = {"n": len(R), "mean %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2),
                                                                   "hit rate": round(float((R > 0).mean()), 3), "t": round(float(R.mean() / (R.std() / np.sqrt(len(R)))), 2)}
    print(d, out[list(out)[-1]], flush=True)
(ROOT / "results/v99/r16c_placebo.json").write_text(json.dumps(out, indent=1))
