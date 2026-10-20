"""Gen181 (config/gen181_protocol.json): short equities before month end (dash for cash). Writes results/gen181.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen159_fomc_cycle.py")}; exec(open(ROOT / "scripts/gen159_fomc_cycle.py").read().split("FAM = {")[0], c)
F, S, TUNE, JUDGE, h, IX, EQ, D, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "IX", "EQ", "D", "daily_book"))


def sleeve(k0, k1):
    m = pd.Series(0.0, index=IX)
    for _, gg in IX.to_series().groupby(IX.to_period("M")):
        n = len(gg)
        if n >= -k0:
            m.loc[gg.index[n + k0:n + k1 + 1]] = 1.0
    return daily_book(pd.DataFrame({r: -0.25 * m for r in EQ}), EQ)


res = []
for k0, k1 in ((-7, -3), (-6, -3), (-5, -3)):
    p = sleeve(k0, k1); res.append((S(p, TUNE), {"k0": k0, "k1": k1}, p)); print(k0, k1, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["DC"] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen181_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen181.json", "w"), indent=1)
