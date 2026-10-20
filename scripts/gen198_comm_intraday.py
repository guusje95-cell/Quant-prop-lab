"""Gen198 (config/gen198_protocol.json): first-hour -> last-hour momentum in commodity futures. Writes results/gen198.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
HOURS = {**{r: (9, 13) for r in ("CL", "NG", "RB", "HO")}, **{r: (8, 12) for r in ("GC", "SI", "HG")}, **{r: (9, 13) for r in ("ZC", "ZS", "ZW")}}
DAT = {}
for r, (h1, h2) in HOURS.items():
    f = F.front(r); t = F.ny(f.index); x = pd.DataFrame({"r": f.r.astype(float).to_numpy(), "h": t.h.to_numpy(), "d": t.date.to_numpy(), "id": f.instrument_id.to_numpy(),
                                                           "c": f.close.astype(float).to_numpy()}, index=f.index)
    x = x[t.wd.to_numpy() < 5]
    a = x[x.h == h1].groupby("d").agg(r1=("r", "sum"), id1=("id", "last")); b = x[x.h == h2].groupby("d").agg(r2=("r", "sum"), id2=("id", "last"), c=("c", "last"))
    y = a.join(b, how="inner"); y = y[y.id1 == y.id2]; y["cost"] = F.cost_frac(r, y.c); y["sd"] = y.r1.rolling(60, min_periods=40).std().shift(1)
    DAT[r] = y


def sleeve(filt):
    out = []
    for r, y in DAT.items():
        s = np.sign(y.r1)
        if filt:
            s = s.where(y.r1.abs() > y.sd, 0.0)
        out.append((s * y.r2 - s.abs() * 2 * y.cost) / len(DAT))
    p = pd.concat(out, axis=1).fillna(0.0).sum(axis=1); p.index = pd.DatetimeIndex(p.index); return p[p.index.weekday < 5]


res = {f: sleeve(f) for f in (False, True)}
sc = {f: [round(F.sharpe(p, *s), 3) for s in F.SPLITS] for f, p in res.items()}; print(sc)
ch = max(res, key=lambda f: F.sharpe(res[f], *B.TUNE)); v = sc[ch]
out = {"splits 2010-17 / 2018-22 / 2023-26": {str(k): v_ for k, v_ in sc.items()}, "chosen filter": ch, "pass": bool(v[0] > 0 and v[1] >= 0.3 and v[2] >= 0.3)}
gross = {}
for f in (False, True):
    gg = []
    for r, y in DAT.items():
        s = np.sign(y.r1); s = s.where(y.r1.abs() > y.sd, 0.0) if f else s; gg.append(s * y.r2 / len(DAT))
    gp = pd.concat(gg, axis=1).fillna(0.0).sum(axis=1); gp.index = pd.DatetimeIndex(gp.index); gross[str(f)] = [round(F.sharpe(gp, *s), 3) for s in F.SPLITS]
out["gross (report)"] = gross
if out["pass"]:
    out.update(B.judge({"CIM": res[ch]}, "gen198"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen198.json", "w"), indent=1)
