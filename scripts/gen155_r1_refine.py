"""Gen155 (config/gen155_protocol.json): R1 refinement at the executable 14:00 ET snapshot. Writes results/gen155.json."""
import itertools
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
S = lambda p, w: F.sharpe(p, *w)
EQ = ["ES", "NQ", "RTY", "YM"]


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def snaps(r, hour=14):
    f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
    m = wk & (t.h == hour - 1).to_numpy(); c = pz[m].groupby(t.date[m]).last()
    rth = wk & (t.h >= 9).to_numpy() & (t.h < hour).to_numpy()
    hi = np.maximum(pz[rth].groupby(t.date[rth]).max().reindex(c.index), c); lo = np.minimum(pz[rth].groupby(t.date[rth]).min().reindex(c.index), c)
    return c, hi, lo, F.daily(r).cost.reindex(c.index).ffill()


SN = {r: snaps(r) for r in EQ}


def r1v(ind, size, hold):
    out = {}
    for r in EQ:
        c, hi, lo, cost = SN[r]; ibs = (c - lo) / (hi - lo); ret = c.pct_change(); sd20 = ret.rolling(20).std()
        z = [rsi2(c) < 10, c <= c.rolling(5).min(), c.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
        if ind == 6:
            z += [c < c.rolling(20).mean() - 2 * c.rolling(20).std(), c.pct_change(2) < -1.5 * sd20]
        sig = (sum(x.astype(float) for x in z) / len(z)).where(hi > lo, 0.0)
        if hold == 48:
            sig = np.maximum(sig, sig.shift(1).fillna(0.0))
        v20, v250 = ret.rolling(20).std(), ret.rolling(250, min_periods=120).std()
        mult = {"const": 1.0, "highvol": (v20 / v250).clip(upper=2), "lowvol": (v250 / v20).clip(upper=2)}[size]
        w = (0.25 * sig * mult).fillna(0.0)
        nxt = c.shift(-1) / c - 1; nxt[(c.index.to_series().diff(-1).dt.days < -4).to_numpy()] = np.nan
        flat = 2 * w.abs() if os.environ.get("QPL_DAILY_FLAT") == "1" else 0.0   # daily 16:10 flat + 18:00 reopen
        out[r] = (w * nxt - (w.diff().abs().fillna(w) + flat) * cost).shift(1)
    p = pd.DataFrame(out).sum(axis=1); return p[p.index.weekday < 5]


if __name__ == "__main__":
    rep, best = [], None
    for ind, size, hold in itertools.product((4, 6), ("const", "highvol", "lowvol"), (24, 48)):
        p = r1v(ind, size, hold); st = S(p, TUNE); rep.append({"ind": ind, "size": size, "hold": hold, "tune": round(st, 3), "2023-26": round(S(p, JUDGE), 3)})
        print(rep[-1], flush=True)
        if best is None or st > best[0]:
            best = (st, rep[-1], p)
    src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
    exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    ref = h["build"](base, "sharpe-weighted"); base2 = base.copy(); base2["R1"] = best[2]; book = h["build"](base2, "sharpe-weighted")
    out = {"grid": rep, "chosen": best[1], "reference 2023-26": round(S(ref, JUDGE), 3), "book 2023-26": round(S(book, JUDGE), 3),
           "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > 0.815)
    print(json.dumps({k: v for k, v in out.items() if k != "grid"})); json.dump(out, open(ROOT / "results/gen155.json", "w"), indent=1)
    if out["adopt"]:
        base2.to_parquet(ROOT / "results/book_sleeves_current.parquet"); book.to_frame("book").to_parquet(ROOT / "results/gen155_book.parquet")
