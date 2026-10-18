"""Gen99 (config/gen99_protocol.json): altcoin bounce in the swap-free CFD book and in v6. Writes results/gen99.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen91_oi.py")}
exec(open(ROOT / "scripts/gen91_oi.py").read().split("G90 = pd.read_parquet")[0], g)
CS, B, CFD, fhp, d2h, IDX, dsh, oi_weights = (g[k] for k in ("CS", "B", "CFD", "fhp", "d2h", "IDX", "dsh", "oi_weights"))
per = lambda h: (dsh(h, "2022-01-01", "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
bper = lambda h: (dsh(h, "2022-01-01", "2026-09-30"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
ROWS = []
# S1 swap-free book
S0 = g["ns"]["sleeves"](0.0, 1.0).reindex(IDX).fillna(0.0)
bb0 = fhp(d2h(oi_weights(["BTC", "ETH"]).reindex(columns=CFD).fillna(0.0)), 0.0).reindex(IDX).fillna(0.0)
SF = {**{k: S0[k] for k in ("C*", "premium carry", "trend 4h", "Weiss expiry")}, "delev bounce": bb0}
alts = [c for c in CFD if c not in ("BTC", "ETH")]
s1 = fhp(d2h(oi_weights(alts).reindex(columns=CFD).fillna(0.0)), 0.0).reindex(IDX).fillna(0.0)
pf = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
b0, b1 = bper(pf(SF)), bper(pf({**SF, "alt bounce": s1})); p = per(s1)
r = {"test": "S1 alt bounce in swap-free CFD book", "DEV": p[0], "TEST": p[1], "HOLD": p[2], "book before (all/TEST/HOLD)": np.round(b0, 3).tolist(),
     "book after (all/TEST/HOLD)": np.round(b1, 3).tolist()}
r["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and b1[0] > b0[0] and b1[1] >= b0[1] and b1[2] >= b0[2]); ROWS.append(r); print(r, flush=True)
# S2 v6
H5 = CS.v5_sleeves(); bounce = CS.delev_bounce()
oth = [c for c in B.coins() if c not in ("BTC", "ETH")]
s2 = CS._from_daily_weights(oi_weights(oth) * 2 / len(oth), oth, 5).loc[:"2026-09-30 23:00"]          # same total budget as the BTC/ETH sleeve
H6 = pd.concat([H5, bounce.rename("delev bounce")], axis=1).fillna(0.0)
v0, v1 = bper(CS.portfolio_v5(H6)[0]), bper(CS.portfolio_v5(pd.concat([H6, s2.rename("alt bounce")], axis=1).fillna(0.0))[0]); p = per(s2)
cst = H5["C*"].groupby(H5.index.floor("D")).sum(); cc = float(pd.concat([cst, s2.groupby(s2.index.floor("D")).sum()], axis=1).loc["2022":].corr().iloc[0, 1])
r = {"test": "S2 alt bounce in v6 (perp)", "DEV": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": cc, "book before (all/TEST/HOLD)": np.round(v0, 3).tolist(),
     "book after (all/TEST/HOLD)": np.round(v1, 3).tolist()}
r["pass"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and cc <= 0.3 and v1[0] > v0[0] and v1[1] >= v0[1] and v1[2] >= v0[2]); ROWS.append(r); print(r, flush=True)
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen99.csv", index=False)
print("done", flush=True)
