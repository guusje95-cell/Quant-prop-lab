"""Gen213 (config/gen213_protocol.json): cascade limit buys on ES/NQ. Writes results/gen213.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
DAT = {}
for r in ("ES", "NQ"):
    f = F.front(r); td = F.trade_date(f.index)
    # price levels on the current contract: use raw close/low, and reject days with a roll inside (ids > 1)
    g = pd.DataFrame({"low": f.low.astype(float).to_numpy(), "close": f.close.astype(float).to_numpy(), "id": f.instrument_id.to_numpy()}, index=f.index).groupby(td)
    d = pd.DataFrame({"low": g.low.min(), "close": g.close.last(), "ids": g.id.nunique(), "id": g.id.last()})
    d = d[d.index.weekday < 5]
    rr = F.daily(r).r.reindex(d.index); d["sd"] = rr.rolling(20).std().shift(1)
    d["prev"] = d.close.shift(1).where(d.id.shift(1) == d.id); d["next"] = d.close.shift(-1).where(d.id.shift(-1) == d.id)
    d["tick"] = F.SPEC[r][0]; d["cost"] = F.cost_frac(r, d.close)
    DAT[r] = d


def sleeve(k, exit_):
    out = []
    for r, d in DAT.items():
        L = d.prev * (1 - k * d.sd); fill = (d.low <= L - d.tick) & (d.ids == 1)
        px = d.close if exit_ == "X0" else d.next
        ret = (px / L - 1 - 2 * d.cost).where(fill)
        p = 0.5 * ret.fillna(0.0)
        if exit_ == "X1":
            p = p.shift(1).fillna(0.0)                 # P&L realised on the exit day
        out.append(p)
    return pd.concat(out, axis=1).fillna(0.0).sum(axis=1)


res = []
for k in (1.5, 2.0):
    for e in ("X0", "X1"):
        p = sleeve(k, e); n = int((p != 0).sum()); res.append((F.sharpe(p, *B.TUNE), {"k": k, "exit": e}, p)); print(k, e, "trades", n, round(res[-1][0], 3), round(F.sharpe(p, *B.JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(F.sharpe(p, *B.JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"CASC": p}, "gen213"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen213.json", "w"), indent=1)
