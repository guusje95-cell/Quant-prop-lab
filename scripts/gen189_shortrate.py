"""Gen189 (config/gen189_protocol.json): equity timing by lagged ZT return. Writes results/gen189.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, h, EQ, daily_book, PX, monthly = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "EQ", "daily_book", "PX", "monthly"))


def sleeve(L):
    p = monthly(np.sign(PX("ZT") / PX("ZT").shift(L) - 1), lambda v: 1.0 if v > 0 else 0.0)
    return daily_book(pd.DataFrame({r: 0.25 * p for r in EQ}), EQ)


res = []
for L in (21, 63):
    p = sleeve(L); res.append((S(p, TUNE), {"L": L}, p)); print(L, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["SR"] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.137)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen189_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen189.json", "w"), indent=1)
