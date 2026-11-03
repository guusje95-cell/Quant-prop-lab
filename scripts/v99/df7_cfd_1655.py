"""DF-7 (deployment, 0 alpha trials): the 8 equity-index sleeves daily-flat with the exit at 16:55 ET instead of 15:55 (CFD firms: the
swap is charged at the 17:00 ET rollover, so the 16:00-17:00 ET hour can be held; Lucid / Tradeify futures close at 16:45). Patched bars
with QPL_FLAT_FROM=17 (the 16:00 ET bar is earned; session-open gaps still not earned) + one extra round trip per held day.
Writes results/v99/df7_cfd_1655.json and results/v99/df7_sleeves.parquet."""
import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"; os.environ["QPL_FLAT_FROM"] = "17"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat
F = dailyflat.patch()
import fbook
src = (ROOT / "scripts/futures_book_build.py").read_text().split("\nb = B.build(P)")[0]
gb = {"__file__": str(ROOT / "scripts/futures_book_build.py"), "__name__": "fbb"}; exec(compile(src, "fbb", "exec"), gb)
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
P = gb["P"][EQ]; P.to_parquet(ROOT / "results/v99/df7_sleeves.parquet")
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out = {"daily-flat 15:55 exit (DF-3)": [0.258, 0.785, 1.164], "daily-flat 16:55 exit (CFD firms)": per(fbook.build(P)),
       "sleeves 16:55": {c: per(P[c]) for c in EQ}}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df7_cfd_1655.json").write_text(json.dumps(out, indent=1))
