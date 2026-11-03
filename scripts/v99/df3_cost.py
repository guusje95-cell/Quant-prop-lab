"""DF-3 cost check (0 trials): exact daily-flat sleeves rebuilt with 1.5x and 2x costs per side; equity-index book and all-15 book.
Writes results/v99/df3_cost.json."""
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
mult = float(sys.argv[1]); orig = F.cost_frac; F.cost_frac = lambda r, p: mult * orig(r, p)
src = (ROOT / "scripts/futures_book_build.py").read_text().split("\nb = B.build(P)")[0]
gb = {"__file__": str(ROOT / "scripts/futures_book_build.py"), "__name__": "fbb"}; exec(compile(src, "fbb", "exec"), gb)
P = gb["P"]; EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
f = ROOT / "results/v99/df3_cost.json"; out = json.loads(f.read_text()) if f.exists() else {}
out[f"{mult}x costs"] = {"equity-index book": per(fbook.build(P[EQ])), "all 15": per(fbook.build(P))}
print(json.dumps(out, indent=1)); f.write_text(json.dumps(out, indent=1))
