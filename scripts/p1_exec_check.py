"""Execution check of P1 (IBS < 0.3 long, ES+NQ, Gen205): signal and fill at an intraday snapshot (ET), 24h hold, vs the
daily-close version in the book. Diagnostic (no new trial). Writes results/p1_exec_check.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B


def snap(hour, members=("ES", "NQ")):
    out = {}
    for r in members:
        f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
        m = wk & (t.h == hour - 1).to_numpy(); c = pz[m].groupby(t.date[m]).last()
        rth = wk & (t.h >= 9).to_numpy() & (t.h < hour).to_numpy()
        hi = np.maximum(pz[rth].groupby(t.date[rth]).max().reindex(c.index), c); lo = np.minimum(pz[rth].groupby(t.date[rth]).min().reindex(c.index), c)
        sig = (((c - lo) / (hi - lo)) < 0.3).astype(float).where(hi > lo, 0.0); w = 0.5 * sig
        nxt = c.shift(-1) / c - 1; nxt[(c.index.to_series().diff(-1).dt.days < -4).to_numpy()] = np.nan
        out[r] = (w * nxt - w.diff().abs().fillna(w) * F.daily(r).cost.reindex(c.index).ffill()).shift(1)
    p = pd.DataFrame(out).sum(axis=1); return p[p.index.weekday < 5]


cur = B.sleeves()["P1"]
res = {"book P1 (daily close fill)": [round(F.sharpe(cur, *s), 3) for s in F.SPLITS]}
for h in (15, 16):
    p = snap(h); res[f"snapshot {h}:00 ET"] = [round(F.sharpe(p, *s), 3) for s in F.SPLITS]
print(json.dumps(res, indent=1)); json.dump(res, open(ROOT / "results/p1_exec_check.json", "w"), indent=1)
