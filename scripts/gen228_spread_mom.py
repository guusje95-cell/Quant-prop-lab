"""Gen228 (config/gen228_protocol.json): calendar-spread momentum. Writes results/gen228.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
U = ["CL", "NG", "HO", "RB", "ZC", "ZS", "LE", "HE"]
DAT = {}
for r in U:
    d = F.daily(r); s2 = F.daily_second(r).reindex(d.index)
    x = pd.DataFrame({"r1": d.r, "r2": s2, "roll": d.roll, "c1": d.cost, "c2": F.cost_frac(r, d.close2)}).dropna(subset=["r1", "r2"])
    x = x[x.index.weekday < 5]; x["s"] = x.r1 - x.r2; x["vol"] = (x.s.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
    DAT[r] = x


def sleeve(L):
    out = []
    for r, x in DAT.items():
        w = (np.sign(x.s.rolling(L).sum()) * 0.10 / x.vol / len(U)).shift(1).where(lambda z: np.isfinite(z), 0.0).fillna(0.0)
        cst = (x.c1 + x.c2.fillna(x.c1))
        out.append(w * x.s - w.diff().abs().fillna(w.abs()) * cst - 2 * w.abs() * x.roll.fillna(0) * cst)
    return pd.concat(out, axis=1).fillna(0.0).sum(axis=1)


res = []
for L in (21, 63):
    p = sleeve(L); res.append((F.sharpe(p, *B.TUNE), L, p)); print(L, round(res[-1][0], 3), round(F.sharpe(p, *B.JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, L, p = res[0]
out = {"best L": L, "tune": round(s, 3), "2023-26": round(F.sharpe(p, *B.JUDGE), 3), "corr with current book (2010-22)": None, "enters": bool(s > 0.3)}
bk = pd.read_parquet(ROOT / "results/gen221_book.parquet").book
out["corr with current book (2010-22)"] = round(float(pd.concat([p, bk], axis=1).dropna().loc[:"2022"].corr().iloc[0, 1]), 2)
if out["enters"]:
    out.update(B.judge({"CSM": p}, "gen228"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen228.json", "w"), indent=1)
