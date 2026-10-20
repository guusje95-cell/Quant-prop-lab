"""Gen151 (config/gen151_protocol.json): short 14:00 -> 16:00 ET on R1 dip days, RTY/YM futures and US index CFDs. Writes results/gen151.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen149_overnight_r1.py")}; exec(open(ROOT / "scripts/gen149_overnight_r1.py").read().split("S = lambda")[0], g)
F, I, FS, signal = g["F"], g["I"], g["FS"], g["signal"]


def fut(root):
    f = F.front(root); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
    pick = lambda h: pz[wk & (t.h == h).to_numpy()].groupby(t.date[wk & (t.h == h).to_numpy()]).last()
    c14, c16 = pick(13), pick(15); rth = wk & (t.h >= 9).to_numpy() & (t.h <= 13).to_numpy()
    hi = pz[rth].groupby(t.date[rth]).max().reindex(c14.index); lo = pz[rth].groupby(t.date[rth]).min().reindex(c14.index)
    cst = F.daily(root).cost.reindex(c14.index).ffill()
    return (signal(c14, hi, lo) * (-(c16.reindex(c14.index) / c14 - 1) - 2 * cst)).fillna(0.0)


def cfd(sym, cost):
    B = I["bars_cfd"](sym); B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    m14, m16 = t < "14:00", t < "16:00"; rth = (t >= "09:30") & m14
    c = B.close[m14].groupby(day[m14]).last(); e = B.close[m16].groupby(day[m16]).last().reindex(c.index)
    hi = B.high[rth].groupby(day[rth]).max().reindex(c.index); lo = B.low[rth].groupby(day[rth]).min().reindex(c.index)
    return (signal(c, hi, lo) * (-(e / c - 1) - 2 * cost)).fillna(0.0)


S = lambda p, spl: [round(F.sharpe(p, a, b), 3) for a, b in spl]
res = {}
fu = {r: fut(r) for r in ("RTY", "YM")}
for r, p in fu.items():
    res[r] = S(p, FS)
res["set 1 RTY+YM"] = S(pd.concat(fu, axis=1).fillna(0.0).sum(axis=1), FS)
for cost in (1e-4, 2e-4):
    cf = {s: cfd(s, cost) for s in ("US100", "US500", "US30")}
    for s, p in cf.items():
        res[f"{s} {cost * 1e4:.0f}bp"] = S(p, I["SPL"])
    res[f"set 2 CFDs {cost * 1e4:.0f}bp"] = S(pd.concat(cf, axis=1).fillna(0.0).sum(axis=1), I["SPL"])
ok = lambda v: all(x > 0 for x in v) and np.mean(v) >= 0.5
res["pass set 1"] = bool(ok(res["set 1 RTY+YM"])); res["pass set 2"] = bool(ok(res["set 2 CFDs 1bp"]))
print(json.dumps(res)); json.dump(res, open(ROOT / "results/gen151.json", "w"), indent=1)
