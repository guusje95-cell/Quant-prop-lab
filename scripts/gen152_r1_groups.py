"""Gen152 (config/gen152_protocol.json): R1 ensemble by futures group, executable snapshot one hour before session end. Writes results/gen152.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
S = lambda p, w: F.sharpe(p, *w)
GROUPS = json.load(open(ROOT / "config/gen152_protocol.json"))["groups"]


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def snap(root):
    f = F.front(root); td = F.trade_date(f.index); pz = (1 + f.r.fillna(0.0)).cumprod()
    pos = f.groupby(td).cumcount(ascending=False)              # 0 = last bar of the trade date
    keep = (pos >= 1).to_numpy(); x = pz[keep]; d = td[keep]
    c = x.groupby(d).last(); hi = x.groupby(d).max(); lo = x.groupby(d).min()
    c = c[c.index.weekday < 5]
    return c, hi.reindex(c.index), lo.reindex(c.index)


SN = {r: snap(r) for g in GROUPS.values() for r in g}


def sleeve(members, longonly):
    out = []
    for r in members:
        c, hi, lo = SN[r]; ibs = (c - lo) / (hi - lo); rs = rsi2(c); dc = c.diff()
        L = sum(z.astype(float) for z in [rs < 10, c <= c.rolling(5).min(), dc.lt(0).rolling(3).sum() == 3, ibs < 0.3]) / 4
        Sh = sum(z.astype(float) for z in [rs > 90, c >= c.rolling(5).max(), dc.gt(0).rolling(3).sum() == 3, ibs > 0.7]) / 4
        sig = (L if longonly else L - Sh).where(hi > lo, 0.0)
        ret = c.pct_change(); vol = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
        w = (sig * 0.10 / vol / len(members)).where(np.isfinite, 0.0)
        cst = F.daily(r).cost.reindex(c.index).ffill()
        out.append(w.shift(1) * ret - w.diff().abs().fillna(w.abs()) * 2 * cst)
    return pd.concat(out, axis=1).fillna(0.0).sum(axis=1)


if __name__ == "__main__":
    rep, enter = {}, {}
    for gname, mem in GROUPS.items():
        res = []
        for lo_ in (True, False):
            p = sleeve(mem, lo_); res.append((S(p, TUNE), lo_, p)); print(gname, lo_, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
        res.sort(key=lambda x: -x[0]); s, lo_, p = res[0]
        rep[gname] = {"long only": lo_, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
        if s > 0.3:
            enter["R1-" + gname] = p
    src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
    exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
    B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {k: h[k.lower()] for k in ("F3", "F5", "G1", "P1", "A3")}
    b0 = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
    e143 = pd.read_parquet(ROOT / "results/gen143_entrants.parquet"); s146 = pd.read_parquet(ROOT / "results/gen146_sleeves.parquet")
    x = {"__file__": str(ROOT / "scripts/gen146_exec_check.py")}; exec(open(ROOT / "scripts/gen146_exec_check.py").read().split("res = {}")[0], x)
    base = {**b0, **{c: e143[c] for c in e143}, "R1": x["snap_book"](14), "T1": s146["T1"], "T2": s146["T2"]}
    ref = h["build"](pd.DataFrame(base), "sharpe-weighted"); book = h["build"](pd.DataFrame({**base, **enter}), "sharpe-weighted")
    out = {"groups": rep, "entered": list(enter), "reference 2023-26": round(S(ref, JUDGE), 3), "book 2023-26": round(S(book, JUDGE), 3),
           "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > 0.815)
    print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen152.json", "w"), indent=1)
    book.to_frame("book").to_parquet(ROOT / "results/gen152_book.parquet")
