"""DF-8 (research/v99/df8_protocol.json). Writes results/v99/df8.json."""
import json
import os
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat
F = dailyflat.patch()
import fbook
g = {"__file__": str(ROOT / "scripts/r1_overnight_dailyflat.py"), "__name__": "r1on"}
exec((ROOT / "scripts/r1_overnight_dailyflat.py").read_text().split("\nP = pd.read_parquet")[0], g)
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet").drop(columns=["CX4", "CXB"])
on = g["r1_on"]().reindex(Q.index).fillna(0.0); Q2 = Q.copy(); Q2["R1"] = 0.5 * Q["R1"] + 0.5 * on
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
out = {"equity book ref": per(fbook.build(Q[EQ])), "equity book R1 mix": per(fbook.build(Q2[EQ])), "all-15 ref": per(fbook.build(Q)), "all-15 R1 mix": per(fbook.build(Q2)),
       "R1 / R1-ON / mix sleeves": [per(Q["R1"]), per(on), per(Q2["R1"])]}
out["pass"] = bool(out["equity book R1 mix"][2] >= out["equity book ref"][2] + 0.05 and out["equity book R1 mix"][1] >= out["equity book ref"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df8.json").write_text(json.dumps(out, indent=1))
