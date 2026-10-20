"""Gen207 (config/gen207_protocol.json): index-CFD book with R1 24h vs overnight. Writes results/gen207.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], g)
o = {"__file__": str(ROOT / "scripts/gen150_cfd_overnight.py")}; exec(open(ROOT / "scripts/gen150_cfd_overnight.py").read().split("\nP6 = p6()")[0], o)
sh = lambda x, a, z: float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(252))


def book(Hc):
    Dd = Hc.groupby(Hc.index.floor("D")).sum(); Dd = Dd[Dd.index.weekday < 5]
    w = 1 / Dd.loc["2020-01-01":"2022-12-31"].std(); w = w / w.sum()
    raw = (Dd * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); return (raw * lvl).dropna()


base = {"P6": g["p6"](), "CAL": g["calendar"]()}
V = {"R24": book(pd.DataFrame({**base, "R1": g["r1"](1e-4)}).fillna(0.0).loc[:"2026-09-30 23:00"]),
     "RON": book(pd.DataFrame({**base, "R1": o["r1"](1e-4)}).fillna(0.0).loc[:"2026-09-30 23:00"])}
res = {k: [round(sh(b, "2020-03", "2022"), 3), round(sh(b, "2023", "2024"), 3), round(sh(b, "2025", "2026-09-30"), 3)] for k, b in V.items()}
ch = max(res, key=lambda k: res[k][0]); out = {"fit / 2023-24 / 2025-26": res, "chosen": ch,
                                              "adopt RON": bool(ch == "RON" and res["RON"][1] >= res["R24"][1] and res["RON"][2] >= res["R24"][2])}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen207.json", "w"), indent=1)
if out["adopt RON"]:
    V["RON"].to_frame("book").to_parquet(ROOT / "results/gen207_book.parquet")
