"""Gen149 (config/gen149_protocol.json): R1 overnight variant on RTY/YM futures and US index CFDs. Writes results/gen149.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
I = {"__file__": str(ROOT / "scripts/gen124_intraday.py")}; exec(open(ROOT / "scripts/gen124_intraday.py").read().split("def news(")[0], I)
FS = (("2010-06-01", "2017-12-31"), ("2018-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30"))


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def signal(c, hi, lo):
    ibs = (c - lo) / (hi - lo)
    ind = [(rsi2(c) < 10), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
    return (sum(z.astype(float) for z in ind) / 4).where(hi > lo, 0.0)


def fut_hourly(root):
    f = F.front(root); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
    pick = lambda h: pz[wk & (t.h == h).to_numpy()].groupby(t.date[wk & (t.h == h).to_numpy()]).last()
    c15, c16, c10 = pick(14), pick(15), pick(9)                     # bar closes at 15:00, 16:00, 10:00 ET
    rth = wk & (t.h >= 9).to_numpy() & (t.h <= 14).to_numpy()
    hi = pz[rth].groupby(t.date[rth]).max().reindex(c15.index); lo = pz[rth].groupby(t.date[rth]).min().reindex(c15.index)
    sig = signal(c15, hi, lo)
    nx10 = c10.reindex(c16.index).shift(-1).where((c16.index.to_series().shift(-1) - c16.index.to_series()).dt.days.le(4))
    cst = F.daily(root).cost.reindex(c16.index).ffill()
    p = (sig.reindex(c16.index) * (nx10 / c16 - 1 - 2 * cst)).fillna(0.0)    # pz is roll-safe, so roll days are fine
    p.index = p.index + pd.Timedelta(days=1); return p


def cfd_5m(sym, cost):
    B = I["bars_cfd"](sym); B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    m55 = t < "15:55"; m16 = t < "16:00"; rth = (t >= "09:30") & m55
    c = B.close[m55].groupby(day[m55]).last(); e = B.close[m16].groupby(day[m16]).last()
    hi = B.high[rth].groupby(day[rth]).max().reindex(c.index); lo = B.low[rth].groupby(day[rth]).min().reindex(c.index)
    o = B.open[t == "09:30"].groupby(day[t == "09:30"]).first()
    sig = signal(c, hi, lo)
    nxo = o.reindex(e.index).shift(-1).where((e.index.to_series().shift(-1) - e.index.to_series()).dt.days.le(4))
    p = (sig.reindex(e.index) * (nxo / e - 1 - 2 * cost)).fillna(0.0); p.index = p.index + pd.Timedelta(days=1); return p


S = lambda p, spl: [round(F.sharpe(p, a, b), 3) for a, b in spl]
res = {}
fut = {r: fut_hourly(r) for r in ("RTY", "YM")}
for r, p in fut.items():
    res[r] = S(p, FS)
s1 = pd.concat(fut, axis=1).fillna(0.0).sum(axis=1); res["set 1 RTY+YM"] = S(s1, FS)
for cost in (1e-4, 2e-4):
    cf = {s: cfd_5m(s, cost) for s in ("US100", "US500", "US30")}
    for s, p in cf.items():
        res[f"{s} {cost * 1e4:.0f}bp"] = S(p, I["SPL"])
    res[f"set 2 CFDs {cost * 1e4:.0f}bp"] = S(pd.concat(cf, axis=1).fillna(0.0).sum(axis=1), I["SPL"])
ok = lambda v: all(x > 0 for x in v) and np.mean(v) >= 0.5
res["pass set 1"] = bool(ok(res["set 1 RTY+YM"])); res["pass set 2"] = bool(ok(res["set 2 CFDs 1bp"]))
# report only: the same hourly variant on ES/NQ (seen in Gen148) for comparability
for r in ("ES", "NQ"):
    res[f"{r} hourly variant (seen)"] = S(fut_hourly(r), FS)
print(json.dumps(res, indent=1)); json.dump(res, open(ROOT / "results/gen149.json", "w"), indent=1)
