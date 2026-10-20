"""Gen140 (config/gen140_protocol.json): nested optimisation of the futures book (tune 2010-22, judge 2023-26). Writes results/gen140.json."""
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen127_multi.py").read()
g = {"__file__": str(ROOT / "scripts/gen127_multi.py")}
exec(src[:src.index("# P1 IBS futures")], g)
D, daily_book, daily_hl = g["D"], g["daily_book"], g["daily_hl"]
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
S = lambda p, w: F.sharpe(p, *w)
idx_all = pd.DataFrame({r: D[r].r for r in F.NONCRYPTO}).sort_index().index


def f3(k):
    B3 = ["ZN", "ZB", "ZF"]; R3 = pd.DataFrame({r: D[r].r for r in B3}).sort_index(); SD3 = R3.ewm(span=35, min_periods=30).std()
    W = pd.DataFrame(0.0, index=R3.index, columns=B3)
    for _, gg in R3.index.to_series().groupby(R3.index.to_period("M")):
        if len(gg) < k + 2:
            continue
        d0 = gg.index[-(k + 1)]; iv = 1 / SD3.loc[d0]
        if np.isfinite(iv).all():
            W.loc[gg.index[-k:]] = (iv / iv.sum() * 3 * 0.003 / SD3.loc[d0].mean()).to_numpy()
    return daily_book(W, B3)


def f5(win, cap):
    E = ["ES", "NQ"]; RE = pd.DataFrame({r: D[r].r for r in E}).sort_index(); rv = RE.rolling(win).std() * np.sqrt(252)
    return daily_book((0.5 * (0.15 / rv).clip(upper=cap)).shift(1).fillna(0.0), E)


R24 = pd.DataFrame({r: D[r].r for r in F.NONCRYPTO}).sort_index(); VOL = R24.ewm(span=60, min_periods=40).std() * np.sqrt(252); PX = (1 + R24.fillna(0.0)).cumprod()
ME = R24.index.to_series().groupby(R24.index.to_period("M")).max()


def g1(lbs):
    W = pd.DataFrame(np.nan, index=R24.index, columns=F.NONCRYPTO)
    for d in ME:
        i = R24.index.get_loc(d)
        if i < max(lbs) + 5:
            continue
        s = sum(np.sign(PX.iloc[i] / PX.iloc[i - lb] - 1) for lb in lbs) / len(lbs)
        live = VOL.loc[d].notna() & R24.loc[:d].notna().iloc[-max(lbs):].all()
        W.loc[d] = (s * 0.40 / VOL.loc[d]).where(live, 0.0) / live.sum()
    return daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), F.NONCRYPTO)


EQ = ["ES", "NQ", "RTY", "YM"]; HL = {r: daily_hl(r) for r in EQ}; REQ = pd.DataFrame({r: D[r].r for r in EQ}).sort_index()


def p1(lo, hi, longonly):
    W = {}
    for r in EQ:
        h = HL[r]; ibs = (h.c - h.lo) / (h.hi - h.lo); ok = (h.ids == 1) & (h.hi > h.lo)
        W[r] = pd.Series(np.where(ok & (ibs < lo), 0.25, np.where(ok & (ibs > hi) & (not longonly), -0.25, 0.0)), index=h.index)
    return daily_book(pd.DataFrame(W).reindex(REQ.index).fillna(0.0).shift(1).fillna(0.0), EQ)


a = pd.read_parquet(ROOT / "research_data/more2/treasury_auctions.parquet"); a = a[a.securityType.isin(["Note", "Bond"])].copy(); a["date"] = pd.to_datetime(a.auctionDate)
sub = {"ZT": lambda t, s: t == "Note" and s == "2-Year", "ZF": lambda t, s: t == "Note" and s == "5-Year",
       "ZN": lambda t, s: t == "Note" and (s.startswith("10-Year") or s.startswith("9-Year")), "ZB": lambda t, s: t == "Bond" and (s.startswith("30-Year") or s.startswith("29-Year"))}
a["root"] = [next((k for k, f in sub.items() if f(t, s)), None) for t, s in zip(a.securityType, a.securityTerm)]; a = a.dropna(subset=["root"])
MR = ["ZT", "ZF", "ZN", "ZB"]; RR = pd.DataFrame({r: D[r].r for r in MR}).sort_index(); VR = RR.rolling(60).std() * np.sqrt(252)


def a3(pre, post):
    W = pd.DataFrame(0.0, index=RR.index, columns=MR); ix = RR.index
    for _, e in a.iterrows():
        if e.date not in ix:
            continue
        i = ix.get_loc(e.date)
        if i < pre + 2 or i + post >= len(ix):
            continue
        s = 0.10 / VR[e.root].iloc[i - pre - 1]
        if np.isfinite(s):
            W.loc[ix[i - pre:i], e.root] = -s; W.loc[ix[i + 1:i + 1 + post], e.root] = s
    return daily_book(W, MR)


GRID = {"F3": ({"k": k} for k in (2, 3, 4, 5)), "F5": ({"win": w, "cap": c} for w in (10, 20, 40, 60) for c in (1.5, 2, 3)),
        "G1": ({"lbs": l} for l in ((63,), (126,), (252,), (63, 126, 252))),
        "P1": ({"lo": lo, "hi": hi, "longonly": lo_} for (lo, hi) in ((0.1, 0.9), (0.2, 0.8), (0.3, 0.7)) for lo_ in (False, True)),
        "A3": ({"pre": p, "post": q} for p in (3, 5, 7) for q in (2, 4, 6))}
FN = {"F3": f3, "F5": f5, "G1": g1, "P1": p1, "A3": a3}
DEFAULT = {"F3": {"k": 3}, "F5": {"win": 20, "cap": 2}, "G1": {"lbs": (252,)}, "P1": {"lo": 0.2, "hi": 0.8, "longonly": False}, "A3": {"pre": 4, "post": 4}}
chosen, best_p, grid_report = {}, {}, {}
for k, gen in GRID.items():
    res = []
    for prm in gen:
        p = FN[k](**prm); res.append((S(p, TUNE), prm, p))
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    chosen[k] = {"params": {kk: (list(v) if isinstance(v, tuple) else v) for kk, v in prm.items()}, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3)}
    best_p[k] = p; grid_report[k] = [(round(x[0], 3), {kk: (list(v) if isinstance(v, tuple) else v) for kk, v in x[1].items()}) for x in res]
    print(k, chosen[k], flush=True)
default_p = {k: FN[k](**DEFAULT[k]) for k in FN}


def build(P, method):
    P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
    if method == "inverse-vol":
        W = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
        for m in P.index[~P.index.to_period("M").duplicated()]:
            h = P.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
            if len(h) >= 120:
                iv = 1 / h.std().replace(0, np.nan); W.loc[m] = (iv / iv.sum()).fillna(0.0)
        W = W.ffill()
    else:
        T = P.loc[TUNE[0]:TUNE[1]]
        if method == "sharpe-weighted":
            w = (T.mean() / T.std()).clip(lower=0) / T.std(); w = w / w.sum()
        else:
            from scipy.optimize import minimize
            C = T.cov().to_numpy(); n = len(C)
            w = pd.Series(minimize(lambda x: x @ C @ x, np.ones(n) / n, bounds=[(0, 1)] * n, constraints=({"type": "eq", "fun": lambda x: x.sum() - 1},)).x, index=P.columns)
        W = pd.DataFrame([w.to_numpy()] * len(P), index=P.index, columns=P.columns)
    raw = (P * W).sum(axis=1).where(W.notna().any(axis=1))
    lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


Pbest = pd.DataFrame(best_p); Pdef = pd.DataFrame(default_p)
cons = {m: build(Pbest, m) for m in ("inverse-vol", "sharpe-weighted", "min-variance")}
cons_tune = {m: round(S(b, TUNE), 3) for m, b in cons.items()}
mbest = max(cons_tune, key=cons_tune.get); book = cons[mbest]
ref = build(Pdef, "inverse-vol")
out = {"chosen per sleeve": chosen, "construction (tune 2010-22 Sharpe)": cons_tune, "chosen construction": mbest,
       "OPTIMISED book 2023-26": round(S(book, JUDGE), 3), "OPTIMISED book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)],
       "reference (Gen135 settings, same code) 2023-26": round(S(ref, JUDGE), 3), "grids": grid_report}
out["adopt optimised"] = bool(out["OPTIMISED book 2023-26"] > out["reference (Gen135 settings, same code) 2023-26"])
print(json.dumps({k: v for k, v in out.items() if k != "grids"}, indent=1)); json.dump(out, open(ROOT / "results/gen140.json", "w"), indent=1)
book.to_frame("book").to_parquet(ROOT / "results/gen140_book.parquet")
