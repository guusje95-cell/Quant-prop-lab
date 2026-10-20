"""Gen201 (config/gen201_protocol.json): stand-alone index-CFD book (P6 + R1 + calendar), EQR. Writes results/gen201.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], g)
p6, r1, calendar = g["p6"], g["r1"], g["calendar"]
H = pd.DataFrame({"P6": p6(), "R1": r1(1e-4), "CAL": calendar()}).fillna(0.0).loc[:"2026-09-30 23:00"]
Dd = H.groupby(H.index.floor("D")).sum(); Dd = Dd[Dd.index.weekday < 5]
fit = Dd.loc["2020-01-01":"2022-12-31"]; w = 1 / fit.std(); w = w / w.sum()
raw = (Dd * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); b = (raw * lvl).dropna()
sh = lambda x, a, z: float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(252))
def dd(x):
    eq = (1 + x).cumprod(); return round(float((eq / eq.cummax() - 1).min()), 3)
out = {"weights": w.round(3).to_dict(), "components 2020-22 / 2023-24 / 2025-26": {c: [round(sh(Dd[c], a, z), 2) for a, z in (("2020", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))] for c in Dd},
       "book 2020-22 (fit) / 2023-24 / 2025-26": [round(sh(b, a, z), 3) for a, z in (("2020-03", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))],
       "max DD 2023-26 at 10% vol": dd(b.loc["2023":]), "by year": {str(y): round(sh(b, str(y), str(y)), 2) for y in range(2020, 2027)},
       "corr with futures book 2023-26": round(float(pd.concat([b, pd.read_parquet(ROOT / "results/gen190_book.parquet").book], axis=1).loc["2023":].corr().iloc[0, 1]), 2)}
v = out["book 2020-22 (fit) / 2023-24 / 2025-26"]; out["pass"] = bool(v[1] >= 0.8 and v[2] >= 0.8)
from qpl.lab import propfirms as PF
f = replace(PF.PRESETS["BrightFunded Two-Step Classic $100k"], fee=591.0)
x = b.loc["2023":]; x = x * 0.15 / (x.std() * np.sqrt(252)); d = pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})
for sc, sf in ((0.5, 0.5), (1.0, 0.5), (1.0, 1.0)):
    pb = PF.pipeline(d, f, 5, 1, sc, sf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    out[f"prop 2023-26 bootstrap, risk {sc}/{sf}"] = {"P_funded": round(pb["P_funded"], 2), "P_profit": round(pb["P_profit"], 2), "net 2y": round(pb["net_mean"]), "p10": round(pb["net_p10"])}
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen201.json", "w"), indent=1); b.to_frame("book").to_parquet(ROOT / "results/gen201_book.parquet")
