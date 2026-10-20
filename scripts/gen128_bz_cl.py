"""Gen128 (config/gen128_protocol.json): Brent-WTI reversion on roll-safe CME BZ/CL futures. Writes results/gen128.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen127_multi.py").read()
g = {"__file__": str(ROOT / "scripts/gen127_multi.py")}
exec(src[:src.index("# P1 IBS futures")] + src[src.index("def pair_book"):src.index("def fut_pair")], g)
D, daily_book, report, rows, pair_book = (g[k] for k in ("D", "daily_book", "report", "rows", "pair_book"))
D["BZ"] = F.daily("BZ")
f = F.front("BZ"); print("BZ:", f.index[0], f.index[-1], "rolls", int(f.roll.sum()), "max |roll r|", round(float(f.r[f.roll == 1].abs().max()), 4), flush=True)
R = pd.DataFrame({"BZ": D["BZ"].r, "CL": D["CL"].r}).dropna(); px = (1 + R).cumprod()
_, wa, wb = pair_book("BZ", "CL", px.BZ, px.CL, 60, 20, None, R, 0, 0)
W = pd.DataFrame({"BZ": wa, "CL": wb})
report("Gen128 Brent-WTI reversion, CME BZ/CL (clean rolls)", daily_book(W, ["BZ", "CL"]), "multi-day")
pd.DataFrame(rows).to_csv(ROOT / "results/gen128.csv", index=False)
