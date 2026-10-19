"""Gen107 (config/gen107_protocol.json): cascade and hourly shock reversal at BrightFunded costs. Writes results/gen107.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen106_intraday.py")}
exec(open(ROOT / "scripts/gen106_intraday.py").read().split("\nb0, H0 = book(pos); k0")[0], g)
CB, B, R, pos, IDX, book, per, sh, sleeve, COST = (g[k] for k in ("CB", "B", "R", "pos", "IDX", "book", "per", "sh", "sleeve", "COST"))
import crypto_sleeves as CS
b0, H0 = book(pos); k0 = per(b0, "2022-01-01"); B0 = sh(b0, "2022-01-01", "2026-09-30")
rows = []


def report(name, h):
    p = per(h); ph = CS.portfolio_v5(pd.concat([H0, h.rename(name)], axis=1).fillna(0.0))[0]
    k1 = per(ph, "2022-01-01"); bA = sh(ph, "2022-01-01", "2026-09-30")
    r = {"test": name, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "book before": B0, "book after": bA, "book TEST/HOLD before": np.round(k0[1:], 3).tolist(),
         "book TEST/HOLD after": np.round(k1[1:], 3).tolist()}
    r["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and bA > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


pnl, cpos = CS.cascade(limit=0.005, through=0.001, coins=["BTC", "ETH"], cost_map={"BTC": float(COST["BTC"]), "ETH": float(COST["ETH"])}, positions=True)
report("C1 cascade strict BTC/ETH at BrightFunded costs", pnl.reindex(IDX).fillna(0.0))
P = pd.DataFrame(0.0, index=IDX, columns=CB.CFD)
for c in ("BTC", "ETH"):
    r = R[c]; sd = r.rolling(24 * 30, min_periods=24 * 10).std().shift(1)
    sig = pd.Series(np.where(r < -3 * sd, 1.0, np.where(r > 3 * sd, -1.0, 0.0)), index=IDX)
    P[c] = 0.5 * sig.shift(1).rolling(3, min_periods=1).mean().clip(-1, 1)
report("C2 hourly shock reversal BTC/ETH at BrightFunded costs", sleeve(P))
pd.DataFrame(rows).to_csv(ROOT / "results/gen107.csv", index=False)
print("done", flush=True)
