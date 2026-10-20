"""Gen146 (config/gen146_protocol.json): equity-index reversal ensemble and calendar effects. Writes results/gen146.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from dateutil.easter import easter
from pandas.tseries.holiday import USFederalHolidayCalendar
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read()
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], g)
exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], g)
F, S, TUNE, JUDGE, build, daily_book, EQ, HL, REQ = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build", "daily_book", "EQ", "HL", "REQ"))


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def r1(th, filt, exit_):
    W = {}
    for r in EQ:
        h = HL[r]; c = (1 + REQ[r].fillna(0.0)).cumprod().reindex(h.index).ffill(); ok = (h.ids == 1) & (h.hi > h.lo)
        ibs = (h.c - h.lo) / (h.hi - h.lo)
        ind = [(rsi2(c) < th), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
        sig = sum(x.astype(float) for x in ind) / 4 * ok
        if filt:
            sig = sig * (c > c.rolling(200).mean())
        if exit_ == "ma5":
            pos, cur, ma = [], 0.0, c.rolling(5).mean()
            for s_, ci, mi in zip(sig.to_numpy(), c.to_numpy(), ma.to_numpy()):
                cur = s_ if s_ > 0 else (0.0 if ci > mi else cur); pos.append(cur)
            sig = pd.Series(pos, index=sig.index)
        W[r] = 0.25 * sig
    return daily_book(pd.DataFrame(W).reindex(REQ.index).fillna(0.0).shift(1).fillna(0.0), EQ)


IX = REQ.index


def t1(pre, post):
    W = pd.Series(0.0, index=IX)
    per = IX.to_period("M"); first = ~pd.Series(per).duplicated().to_numpy(); starts = np.where(first)[0]
    for i in starts[1:]:
        W.iloc[max(0, i - pre):i + post] = 0.25
    return daily_book(pd.DataFrame({r: W for r in EQ}).shift(0), EQ)


hol = set(USFederalHolidayCalendar().holidays("2009-01-01", "2027-12-31")) | {pd.Timestamp(easter(y)) - pd.Timedelta(days=2) for y in range(2009, 2028)}
hol = {d for d in hol if d.weekday() < 5}


def t2(k):
    W = pd.Series(0.0, index=IX)
    for d in hol:
        j = IX.searchsorted(d)
        if 0 < j <= len(IX):
            W.iloc[max(0, j - k):j] = 0.25
    return daily_book(pd.DataFrame({r: W for r in EQ}), EQ)


FAM = {"R1": [(r1, {"th": t, "filt": f, "exit_": e}) for t in (10, 25) for f in (False, True) for e in ("next", "ma5")],
       "T1": [(t1, {"pre": a, "post": b}) for a, b in ((1, 3), (2, 3), (1, 1))],
       "T2": [(t2, {"k": k}) for k in (1, 2)]}
if __name__ == "__main__":
    rep, enter, allp = {}, {}, {}
    for name, opts in FAM.items():
        res = []
        for fn, prm in opts:
            p = fn(**prm); res.append((S(p, TUNE), prm, p))
            print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
        res.sort(key=lambda x: -x[0]); s, prm, p = res[0]; allp[name] = p
        rep[name] = {"best": {k: str(v) for k, v in prm.items()}, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
        if s > 0.3:
            enter[name] = p
    base = pd.read_parquet(ROOT / "results/gen143_entrants.parquet")
    B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {"F3": g["f3"], "F5": g["f5"], "G1": g["g1"], "P1": g["p1"], "A3": g["a3"]}
    b0 = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
    b0.update({c: base[c] for c in base})
    ref = build(pd.DataFrame(b0), "sharpe-weighted"); book = build(pd.DataFrame({**b0, **enter}), "sharpe-weighted")
    out = {"families": rep, "entered": list(enter), "reference (Gen143 book) 2023-26": round(S(ref, JUDGE), 3),
           "book 2023-26": round(S(book, JUDGE), 3), "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > 0.674)
    print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen146.json", "w"), indent=1)
    book.to_frame("book").to_parquet(ROOT / "results/gen146_book.parquet"); pd.DataFrame(allp).to_parquet(ROOT / "results/gen146_sleeves.parquet")
