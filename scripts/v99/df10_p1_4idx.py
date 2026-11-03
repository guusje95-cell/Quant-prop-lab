"""DF-10 (research/v99/df10_protocol.json). Writes results/v99/df10_p1_4idx.json."""
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
g = {"__file__": str(ROOT / "scripts/p1_exec_check.py"), "__name__": "p1"}
src = (ROOT / "scripts/p1_exec_check.py").read_text().split("\ncur = B.sleeves()")[0]
exec(src.replace("w = 0.5 * sig", "w = WSIZE * sig"), dict(g, WSIZE=0.25)) if False else None
g["WSIZE"] = 0.25; exec(src.replace("w = 0.5 * sig", "w = WSIZE * sig"), g)
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]
g["WSIZE"] = 0.5; chk = g["snap"](16).reindex(Q.index).fillna(0.0)
g["WSIZE"] = 0.25; p4 = g["snap"](16, members=("ES", "NQ", "RTY", "YM")).reindex(Q.index).fillna(0.0)
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
Q2 = Q.copy(); Q2["P1"] = p4
out = {"P1 check (rebuilt ES+NQ vs saved, corr)": round(float(chk.corr(Q["P1"])), 4), "P1 ES+NQ": per(Q["P1"]), "P1 4 indices": per(p4),
       "equity book ref": per(fbook.build(Q)), "equity book with P1 on 4 indices": per(fbook.build(Q2))}
out["pass"] = bool(out["equity book with P1 on 4 indices"][2] >= out["equity book ref"][2] + 0.05 and out["equity book with P1 on 4 indices"][1] >= out["equity book ref"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df10_p1_4idx.json").write_text(json.dumps(out, indent=1))
