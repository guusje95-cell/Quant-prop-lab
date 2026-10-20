"""FLAGGED analysis (not a clean pre-registered test): R1 held 18:00 -> 10:00 ET (signal at the 16:00 close) on ES+NQ as the R1 sleeve of the
daily-flat (MFFU / Tradeify) book. Evidence: the overnight window was found on ES/NQ (Gen148, contaminated), passed on unseen US index CFDs
(Gen149 set 2) and failed on RTY/YM (Gen149 set 1). Writes results/r1_overnight_dailyflat.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
r1 = {"__file__": str(ROOT / "scripts/gen155_r1_refine.py")}; exec(open(ROOT / "scripts/gen155_r1_refine.py").read().split("SN = {r: snaps")[0], r1)
rsi2 = r1["rsi2"]


def r1_on(members=("ES", "NQ")):
    out = {}
    for r in members:
        f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
        pick = lambda m: pz[m].groupby(t.date[m]).last()
        c16 = pick(wk & (t.h == 15).to_numpy()); c10 = pick(wk & (t.h == 9).to_numpy())
        o18 = pz.shift(1)[(t.h == 18).to_numpy()]; o18 = o18.groupby(t.date[(t.h == 18).to_numpy()]).first()     # price at 18:00 (previous bar's close)
        rth = wk & (t.h >= 9).to_numpy() & (t.h < 16).to_numpy()
        hi = np.maximum(pz[rth].groupby(t.date[rth]).max().reindex(c16.index), c16); lo = np.minimum(pz[rth].groupby(t.date[rth]).min().reindex(c16.index), c16)
        ibs = (c16 - lo) / (hi - lo); ret = c16.pct_change()
        ind = [rsi2(c16) < 10, c16 <= c16.rolling(5).min(), c16.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
        mult = (ret.rolling(250, min_periods=120).std() / ret.rolling(20).std()).clip(upper=2)
        w = 0.5 * (sum(z.astype(float) for z in ind) / 4).where(hi > lo, 0.0) * mult
        entry = o18.reindex(c16.index)                                   # 18:00 on the signal day (same calendar date in ET)
        nx10 = c10.reindex(c16.index).shift(-1).where((c16.index.to_series().shift(-1) - c16.index.to_series()).dt.days.le(4))
        cost = F.daily(r).cost.reindex(c16.index).ffill()
        out[r] = (w * (nx10 / entry - 1 - 2 * cost)).fillna(0.0).shift(1)
    p = pd.DataFrame(out).sum(axis=1); return p[p.index.weekday < 5]


P = pd.read_parquet(ROOT / "results/futures_book_rebuild_sleeves_dailyflat.parquet")
on = r1_on().reindex(P.index).fillna(0.0)
P2 = P.copy(); P2["R1"] = on
b1, b2 = B.build(P), B.build(P2)
out = {"R1-ON sleeve 2010-17 / 2018-22 / 2023-26": [round(F.sharpe(on, *s), 3) for s in F.SPLITS],
       "daily-flat book (R1 24h)": [round(F.sharpe(b1, *s), 3) for s in F.SPLITS], "daily-flat book (R1 overnight)": [round(F.sharpe(b2, *s), 3) for s in F.SPLITS],
       "FLAG": "the overnight window was discovered on ES/NQ (Gen148); treat as weaker evidence than a clean test"}
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/r1_overnight_dailyflat.json", "w"), indent=1)
b2.to_frame("book").to_parquet(ROOT / "results/dailyflat_book_r1on.parquet")
