"""Gen183 (config/gen183_protocol.json): equity timing by lagged crude return. Writes results/gen183.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen159_fomc_cycle.py")}; exec(open(ROOT / "scripts/gen159_fomc_cycle.py").read().split("FAM = {")[0], c)
F, S, TUNE, JUDGE, h, IX, EQ, D, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "IX", "EQ", "D", "daily_book"))
CL = (1 + D["CL"].r.reindex(IX).fillna(0.0)).cumprod()
ME = IX.to_series().groupby(IX.to_period("M")).max()


def sleeve(mode, L):
    s = np.sign(CL / CL.shift(L) - 1)
    pos = pd.Series(np.nan, index=IX)
    for d in ME:
        v = s.loc[d]
        pos.loc[d] = (-v if mode == "LS" else (1.0 if v < 0 else 0.0)) if np.isfinite(v) else 0.0
    pos = pos.ffill().shift(1).fillna(0.0)                      # decided at the month-end close, held from the next day
    return daily_book(pd.DataFrame({r: 0.25 * pos for r in EQ}), EQ)


res = []
for mode in ("LS", "LO"):
    for L in (21, 63):
        p = sleeve(mode, L); res.append((S(p, TUNE), {"mode": mode, "L": L}, p)); print(mode, L, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["OIL"] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen183_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen183.json", "w"), indent=1)
