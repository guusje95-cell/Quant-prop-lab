"""Gen233 (config/gen233_protocol.json): index-CFD book + P1 CFD leg. Writes results/gen233.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], g)
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
H = pd.DataFrame({"P6": g["p6"](), "R1": g["r1"](1e-4), "CAL": g["calendar"](), "P1": q["p1"]()}).fillna(0.0).loc[:"2026-09-30 23:00"]
Dd = H.groupby(H.index.floor("D")).sum(); Dd = Dd[Dd.index.weekday < 5]
w = 1 / Dd.loc["2020-01-01":"2022-12-31"].std(); w = w / w.sum()
raw = (Dd * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); b = (raw * lvl).dropna()
sh = lambda a, z: round(float(b.loc[a:z].mean() / b.loc[a:z].std() * np.sqrt(252)), 3)
eq = (1 + b.loc["2023":]).cumprod()
out = {"weights": w.round(3).to_dict(), "fit / 2023-24 / 2025-26": [sh("2020-03", "2022"), sh("2023", "2024"), sh("2025", "2026-09-30")],
       "Gen201": [0.973, 1.247, 0.988], "max DD 2023-26 at 10% vol": round(float((eq / eq.cummax() - 1).min()), 3),
       "by year": {str(y): sh(str(y), str(y)) for y in range(2020, 2027)}}
v = out["fit / 2023-24 / 2025-26"]; out["pass"] = bool(v[1] >= 1.247 and v[2] >= 0.988)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen233.json", "w"), indent=1)
if out["pass"]:
    b.to_frame("book").to_parquet(ROOT / "results/gen233_book.parquet")
