"""Gen235 (config/gen235_protocol.json): P1 overnight-only vs 24h. Writes results/gen235.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B


def p1_on(members=("ES", "NQ")):
    out = {}
    for r in members:
        f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
        pick = lambda hh: pz[wk & (t.h == hh).to_numpy()].groupby(t.date[wk & (t.h == hh).to_numpy()]).last()
        c16, c10 = pick(15), pick(9)
        rth = wk & (t.h >= 9).to_numpy() & (t.h < 16).to_numpy()
        hi = np.maximum(pz[rth].groupby(t.date[rth]).max().reindex(c16.index), c16); lo = np.minimum(pz[rth].groupby(t.date[rth]).min().reindex(c16.index), c16)
        sig = 0.5 * (((c16 - lo) / (hi - lo)) < 0.3).astype(float).where(hi > lo, 0.0)
        nx = c10.reindex(c16.index).shift(-1).where((c16.index.to_series().shift(-1) - c16.index.to_series()).dt.days.le(4))
        cost = F.daily(r).cost.reindex(c16.index).ffill()
        out[r] = (sig * (nx / c16 - 1 - 2 * cost)).fillna(0.0).shift(1)
    p = pd.DataFrame(out).sum(axis=1); return p[p.index.weekday < 5]


cur = B.sleeves()["P1"]; on = p1_on()
t = {"24h": round(F.sharpe(cur, *B.TUNE), 3), "ON": round(F.sharpe(on, *B.TUNE), 3)}; ch = max(t, key=t.get)
out = {"tune": t, "chosen": ch}
if ch == "ON":
    out.update(B.judge({"P1": on}, "gen235"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen235.json", "w"), indent=1)
