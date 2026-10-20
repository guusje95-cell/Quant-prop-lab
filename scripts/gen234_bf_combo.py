"""Gen234 (config/gen234_protocol.json): bf + ridge + (P6 + R1 + P1 CFD). Writes results/gen234.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1 = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1"))
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
P1 = q["p1"]()
ref = CS.portfolio_v5(pd.concat([HB0, (P6 + R1).rename("vol-managed indices")], axis=1).fillna(0.0))[0]; B0, k0 = sh(ref, "2022-01-01", "2026-09-30"), per(ref, "2022-01-01")
vb = CS.portfolio_v5(pd.concat([HB0, (P6 + R1 + P1).rename("vol-managed indices"), hb.rename("ridge ML")], axis=1).fillna(0.0))[0]
B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
out = {"reference": [round(B0, 3), np.round(k0, 3).tolist()], "book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen234.json", "w"), indent=1)
if out["pass"]:
    vb.to_frame("book").to_parquet(ROOT / "results/gen234_book.parquet")
