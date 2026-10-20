"""Gen148 (config/gen148_protocol.json): R1 edge by holding window on 1-minute ES/NQ. Writes results/gen148.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
I = {"__file__": str(ROOT / "scripts/gen124_intraday.py")}; exec(open(ROOT / "scripts/gen124_intraday.py").read().split("def news(")[0], I)
SPL = I["SPL"]


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def load(root, old=False):
    if not old:
        return I["bars_futures"](root)
    d = pd.read_parquet(F.DB / "NQ_1m_2010_2017.parquet"); d = d[d.symbol.astype(str).str.endswith(".v.0")]
    d.index = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d[~d.index.duplicated()].sort_index()
    return d[["open", "high", "low", "close", "instrument_id"]].astype({"open": float, "high": float, "low": float, "close": float})


def snaps(B):
    B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    def last(mask):
        x = B[mask]; return x.groupby(day[mask]).agg(c=("close", "last"), iid=("instrument_id", "last"))
    o = B[t == "09:30"].groupby(day[t == "09:30"]).agg(c=("open", "first"), iid=("instrument_id", "first"))
    rth = (t >= "09:30") & (t < "14:00"); x = B[rth]; hl = x.groupby(day[rth]).agg(hi=("high", "max"), lo=("low", "min"))
    s = pd.DataFrame({"o": o.c, "oi": o.iid}).join(last(t < "14:00").rename(columns={"c": "p14", "iid": "i14"}), how="outer")
    s = s.join(last(t < "16:00").rename(columns={"c": "p16", "iid": "i16"}), how="outer").join(hl, how="outer")
    return s.dropna()


def windows(root, B):
    s = snaps(B); c = s.p14
    ibs = (c - s.lo) / (s.hi - s.lo)
    ind = [(rsi2(c) < 10), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
    sig = (sum(z.astype(float) for z in ind) / 4).where(s.hi > s.lo, 0.0)
    nx = s.shift(-1); gap_ok = (nx.index.to_series().shift(-1) - s.index.to_series()).dt.days.le(4).to_numpy()
    cst = lambda p: 2 * F.cost_frac(root, p)
    legs = {"A": (s.p16 / s.p14 - 1 - cst(s.p14)).where(s.i14 == s.i16),
            "B": (nx.o / s.p16 - 1 - cst(s.p16)).where((s.i16 == nx.oi) & gap_ok),
            "C": (nx.p16 / nx.o - 1 - cst(nx.o)).where((nx.oi == nx.i16) & gap_ok),
            "D": (nx.p14 / nx.o - 1 - cst(nx.o)).where((nx.oi == nx.i14) & gap_ok)}
    out = {}
    for k, r in legs.items():
        p = (sig * r).fillna(0.0); p.index = p.index + pd.Timedelta(days=1); out[k] = p  # dated (approximately) on the exit day
    return out


res, pooled = {}, {}
for root in ("ES", "NQ"):
    w = windows(root, load(root))
    for k, p in w.items():
        pooled.setdefault(k, []).append(p)
        res[f"{root} {k}"] = [round(I["sharpe"](p, a, b), 3) for a, b in SPL]
wo = windows("NQ", load("NQ", old=True))
for k, p in wo.items():
    res[f"NQ 2010-17 {k}"] = round(I["sharpe"](p, "2010-06-01", "2017-12-31"), 3)
for k, ps in pooled.items():
    p = pd.concat(ps, axis=1).fillna(0.0).sum(axis=1); res[f"ES+NQ {k}"] = [round(I["sharpe"](p, a, b), 3) for a, b in SPL]
pc = res["ES+NQ C"]; res["pass C (Topstep)"] = bool(pc[0] > 0 and pc[1] >= 0.5 and pc[2] >= 0.3 and res["NQ 2010-17 C"] > 0)
print(json.dumps(res, indent=1)); json.dump(res, open(ROOT / "results/gen148.json", "w"), indent=1)
