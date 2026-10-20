"""Gen191 (config/gen191_protocol.json): challenge/funded sizing of the futures book. Writes results/gen191.csv/json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
FIRM = PF.Firm("Swing futures firm 50k (ASSUMED)", 50_000, 150, (0.06,), 0.0, "initial", True, 0.04, "trailing_lock", False,
               2, 0, 0.90, 14, 0.0, False, 0.0, "ASSUMED terms", payout_min=250)
b = pd.read_parquet(ROOT / (sys.argv[1] if len(sys.argv) > 1 else "results/gen190_book.parquet"))["book"]


def frame(a, z):
    x = b.loc[a:z]; x = x * 0.15 / (x.std() * np.sqrt(252)); return pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})


def run(d, sc, sf):
    pb = PF.pipeline(d, FIRM, 5, 1, sc, sf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 2), "P_funded": round(pb["P_funded"], 2), "per_month": round(pb["net_per_month"])}


dt, dj = frame("2010-06-01", "2022-12-31"), frame("2023-01-01", "2026-09-30")
rows = []
for sc in (0.33, 0.5, 0.75, 1.0):
    for sf in (0.25, 0.33, 0.5):
        r = run(dt, sc, sf); rows.append({"challenge": sc, "funded": sf, **{f"tune {k}": v for k, v in r.items()}}); print(rows[-1], flush=True)
T = pd.DataFrame(rows); ok = T[T["tune P_profit"] >= 0.85]
ch = ok.sort_values("tune net", ascending=False).iloc[0] if len(ok) else T.sort_values("tune P_profit", ascending=False).iloc[0]
out = {"chosen": {"challenge": float(ch.challenge), "funded": float(ch.funded)}, "chosen 2023-26": run(dj, float(ch.challenge), float(ch.funded)),
       "default 0.5/0.5 2023-26": run(dj, 0.5, 0.5)}
print(json.dumps(out)); T.to_csv(ROOT / "results/gen191.csv", index=False); json.dump(out, open(ROOT / "results/gen191.json", "w"), indent=1)
