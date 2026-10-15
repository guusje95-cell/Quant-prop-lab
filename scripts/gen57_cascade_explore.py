"""Gen57 B4 EXPLORATORY variants (not pre-registered, 2 extra trials): (1) at most 3 open events at a time (gross <= 0.6),
(2) same + only while BTC's C* signal is positive (bull regime). Writes results/gen57_cascade_explore.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
import gen57_timing as T
import gen57_cascade_robust as R0
from qpl.lab import binance_pack as B, strategies as S

cs = S.CStarTrend(); sig = cs.signal(G.CR, {**cs.defaults(), "btc_leads": True})["BTC"]
bull = (sig > 0).shift(1).fillna(False)                         # known at the start of each day


def trades_full(coin, hold=12, k=3.0, cost=5):
    d = R0.hourly(coin); c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
    r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
    atr = (hi - lo).rolling(14).mean()
    ev = (r < -k * sd) & (doi < -0.05) & (v > vq)
    cv, lov, atv = c.to_numpy(), lo.to_numpy(), atr.to_numpy(); n = len(cv); out = []
    for t in np.flatnonzero(ev.to_numpy()):
        if t + 1 >= n:
            continue
        stop = lov[t] - atv[t]; ex = None
        for j in range(t + 1, min(t + 1 + hold, n)):
            if lov[j] <= stop:
                ex = (j, stop); break
        if ex is None:
            j = min(t + hold, n - 1); ex = (j, cv[j])
        out.append((c.index[t], c.index[ex[0]], coin, ex[1] / cv[t] - 1 - 2 * cost / 1e4))
    return out


allt = sorted([t for c in B.coins() for t in trades_full(c)])
for name, use_bull in (("B4x capped 3 open events", False), ("B4x capped 3 open + BTC bull regime only", True)):
    open_ex = []; pnl = {}
    for t0, t1, coin, ret in allt:
        open_ex = [e for e in open_ex if e > t0]
        if len(open_ex) >= 3 or (use_bull and not bool(bull.reindex([t0.floor("D")]).fillna(False).iloc[0])):
            continue
        open_ex.append(t1); d = t1.floor("D"); pnl[d] = pnl.get(d, 0.0) + 0.2 * ret
    s = pd.Series(pnl).sort_index()
    s = s.reindex(pd.date_range("2021-12-01", "2026-09-30")).fillna(0.0)
    print(name, "worst days:", s.nsmallest(3).round(3).to_dict())
    T.report(name, s, "exploratory")
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen57_cascade_explore.csv", index=False)
