"""Gen479 (config/gen479_protocol.json, FLAGGED): R1 held 16:00 ET -> 10:00 ET next weekday instead of 24 h. Writes results/gen479.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import fbook
import futures_db as F
g = {"__file__": str(ROOT / "scripts/gen155_r1_refine.py")}; exec(open(ROOT / "scripts/gen155_r1_refine.py").read().split("\nif __name__")[0], g)
EQ, SN, rsi2 = g["EQ"], g["SN"], g["rsi2"]


def at_hour(r, hour):
    """roll-safe price level at hour:00 ET (close of the bar that ends then), by New York date"""
    f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); m = ((t.wd < 5) & (t.h == hour - 1)).to_numpy()
    return pz[m].groupby(t.date[m]).last()


legs = {}
for r in EQ:
    c, hi, lo, cost = SN[r]; ibs = (c - lo) / (hi - lo); ret = c.pct_change()
    z = [rsi2(c) < 10, c <= c.rolling(5).min(), c.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
    sig = (sum(x.astype(float) for x in z) / len(z)).where(hi > lo, 0.0)
    mult = (ret.rolling(250, min_periods=120).std() / ret.rolling(20).std()).clip(upper=2)
    w = (0.25 * sig * mult).fillna(0.0)
    p16, p10 = at_hour(r, 16).reindex(c.index), at_hour(r, 10)
    nxt10 = p10.reindex(p10.index.union(c.index)).shift(-1).reindex(c.index)       # 10:00 of the next available weekday
    gap = (pd.Series(c.index, index=c.index).shift(-1) - pd.Series(c.index, index=c.index)).dt.days
    on = (nxt10 / p16 - 1).where(gap <= 4)
    legs[r] = (w * on - 2 * w.abs() * cost).fillna(0.0).shift(1)                       # booked on the next day (as the 24 h R1)
P = pd.DataFrame(legs); s = P.sum(axis=1); s = s[s.index.weekday < 5]
base = fbook.sleeves(); bk = fbook.build(base); ref = [round(F.sharpe(bk, *x), 3) for x in F.SPLITS]
b = fbook.build(base.assign(R1=s.reindex(base.index).fillna(0.0))); r_ = [round(F.sharpe(b, *x), 3) for x in F.SPLITS]
out = {"flag": "post hoc window (Gen148); see protocol", "reference": ref, "R1 24 h (current) alone": list(F.splits(base["R1"])),
       "R1 overnight alone": list(F.splits(s)), "per index": {r: list(F.splits(P[r])) for r in EQ},
       "corr overnight vs 24 h 2023-26": round(float(pd.concat([s, base["R1"]], axis=1).loc["2023":].corr().iloc[0, 1]), 2),
       "book with R1 overnight": r_, "pass": bool(r_[2] >= ref[2] + 0.05 and r_[0] >= ref[0] and r_[1] >= ref[1])}
(ROOT / "results/gen479.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
