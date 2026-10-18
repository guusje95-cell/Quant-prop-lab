"""Gen96 part B2: execution delay per sleeve (only that sleeve late, others on time). Writes results/gen96_delay_split.csv."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen96_risk.py").read().split("base = book()")[0]
g = {"__file__": str(ROOT / "scripts/gen96_risk.py")}; sys.argv = [sys.argv[0], sys.argv[1]]; exec(src, g)
book, sh, POS, fhp, IDX = g["book"], g["sh"], g["POS"], g["fhp"], g["IDX"]
rows = []
for s in POS:
    for k in (0, 1, 2, 3, 6, 24):
        pos = {n: (p.shift(k).fillna(0.0) if n == s else p) for n, p in POS.items()}
        hs = fhp(pos[s], 0.0 if s == "Weiss expiry" else 3.3).reindex(IDX).fillna(0.0)
        rows.append({"sleeve late": s, "hours late": k, "sleeve 2022-26": sh(hs), "book 2022-26": sh(book(pos))}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen96_delay_split.csv", index=False)
