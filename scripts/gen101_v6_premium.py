"""Gen101 (config/gen101_protocol.json): Coinbase premium Q1 in v6 at perp costs. Writes results/gen101.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen88_coinbase.py")}
exec(open(ROOT / "scripts/gen88_coinbase.py").read().split("C85 = pd.read_parquet")[0], g)
CS, zd, dsh = g["CS"], g["zd"], g["dsh"]
w = pd.DataFrame({c: np.where(zd[c] > 1, 0.5, np.where(zd[c] < -1, -0.5, 0.0)) for c in ("BTC", "ETH")}, index=zd.index)
q = CS._from_daily_weights(w, ["BTC", "ETH"], 5).loc[:"2026-09-30 23:00"]
H5 = CS.v5_sleeves(); H6 = pd.concat([H5, CS.delev_bounce().rename("delev bounce")], axis=1).fillna(0.0)
v6 = CS.portfolio_v5(H6)[0]; v7 = CS.portfolio_v5(pd.concat([H6, q.rename("coinbase premium")], axis=1).fillna(0.0))[0]
cst = H5["C*"].groupby(H5.index.floor("D")).sum()
P = lambda h: (dsh(h, "2020-01-01", "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
p = P(q)
r = {"DEV": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": float(pd.concat([cst, q.groupby(q.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]),
     "v6 2022-26": dsh(v6, "2022-01-01", "2026-09-30"), "v6 + premium 2022-26": dsh(v7, "2022-01-01", "2026-09-30"),
     "v6 TEST/HOLD": [round(x, 3) for x in P(v6)[1:]], "v6+ TEST/HOLD": [round(x, 3) for x in P(v7)[1:]]}
r["pass"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v6 + premium 2022-26"] > r["v6 2022-26"])
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame([r]).to_csv(ROOT / "results/gen101.csv", index=False)
