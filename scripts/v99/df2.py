"""DF-2 (research/v99/df2_protocol.json). Writes results/v99/df2.json."""
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
r1src = (ROOT / "scripts/r1_overnight_dailyflat.py").read_text().split("\nP = pd.read_parquet")[0]
g = {"__file__": str(ROOT / "scripts/r1_overnight_dailyflat.py"), "__name__": "r1on"}; exec(r1src, g)
n = {"__file__": str(ROOT / "scripts/gen142_overnight.py"), "__name__": "g142"}
exec((ROOT / "scripts/gen142_overnight.py").read_text().split("\nres = []")[0], n)
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet").drop(columns=["CX4", "CXB"])
ref = fbook.build(Q); out = {"reference (DF-1 exact daily-flat)": per(ref)}
on = g["r1_on"]().reindex(Q.index).fillna(0.0); A = Q.copy(); A["R1"] = on
out["A: R1 overnight sleeve"] = per(on); out["A: book"] = per(fbook.build(A))
nd = n["night"](("ES", "NQ", "RTY", "YM"), 20, 9).reindex(Q.index).fillna(0.0); Bq = Q.copy(); Bq["ND"] = nd
out["B: night drift sleeve"] = per(nd); out["B: book"] = per(fbook.build(Bq))
r = out["reference (DF-1 exact daily-flat)"]
for k in ("A", "B"):
    out[k + " pass"] = bool(out[k + ": book"][2] >= r[2] + 0.05 and out[k + ": book"][1] >= r[1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df2.json").write_text(json.dumps(out, indent=1))
