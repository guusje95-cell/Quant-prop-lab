"""Gen153 (config/gen153_protocol.json): announcement-day premium, Halloween, options-expiry week. Writes results/gen153.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
EQ, BD = ["ES", "NQ", "RTY", "YM"], ["ZT", "ZF", "ZN", "ZB"]
IX = pd.DataFrame({r: D[r].r for r in EQ + BD}).sort_index().index
fomc = set(pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date).dt.normalize())
nfp = set()
for m in pd.period_range("2009-12", "2026-12", freq="M"):
    d12 = pd.Timestamp(m.year, m.month, 12); sat = d12 + pd.Timedelta(days=(5 - d12.weekday()) % 7); nfp.add(sat + pd.Timedelta(days=20))
SETS = {"FOMC": fomc, "NFP": nfp, "FOMC+NFP": fomc | nfp}


def on_days(days, members, size):
    m = pd.Series(IX.isin(list(days)), index=IX).astype(float)
    if size == "vol":
        R = pd.DataFrame({r: D[r].r for r in members}).reindex(IX); v = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
        W = (0.10 / v).mul(m, axis=0) / len(members)
    else:
        W = pd.DataFrame({r: m * size for r in members})
    return daily_book(W.fillna(0.0), members)


def halloween():
    m = pd.Series(IX.month.isin([11, 12, 1, 2, 3, 4]), index=IX).astype(float)
    return daily_book(pd.DataFrame({r: m * 0.25 for r in EQ}), EQ)


def opex():
    third_fri = {pd.Timestamp(p.year, p.month, 1) + pd.offsets.WeekOfMonth(week=2, weekday=4) for p in pd.period_range("2009-12", "2026-12", freq="M")}
    wk = {f - pd.Timedelta(days=k) for f in third_fri for k in range(5)}
    m = pd.Series(IX.isin(list(wk)), index=IX).astype(float)
    return daily_book(pd.DataFrame({r: m * 0.25 for r in EQ}), EQ)


FAM = {"AE": [(lambda s: on_days(SETS[s], EQ, 0.25), {"s": s}) for s in SETS],
       "AB": [(lambda s: on_days(SETS[s], BD, "vol"), {"s": s}) for s in SETS],
       "HW": [(lambda: halloween(), {})], "OX": [(lambda: opex(), {})]}
if __name__ == "__main__":
    rep, enter = {}, {}
    for name, opts in FAM.items():
        res = []
        for fn, prm in opts:
            p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
        res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
        rep[name] = {"best": prm, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
        if s > 0.3:
            enter[name] = p
    B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {k: h[k.lower()] for k in ("F3", "F5", "G1", "P1", "A3")}
    b0 = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
    e143 = pd.read_parquet(ROOT / "results/gen143_entrants.parquet"); s146 = pd.read_parquet(ROOT / "results/gen146_sleeves.parquet")
    x = {"__file__": str(ROOT / "scripts/gen146_exec_check.py")}; exec(open(ROOT / "scripts/gen146_exec_check.py").read().split("res = {}")[0], x)
    base = {**b0, **{c: e143[c] for c in e143}, "R1": x["snap_book"](14), "T1": s146["T1"], "T2": s146["T2"]}
    pd.DataFrame(base).to_parquet(ROOT / "results/book_sleeves_current.parquet")
    ref = h["build"](pd.DataFrame(base), "sharpe-weighted"); book = h["build"](pd.DataFrame({**base, **enter}), "sharpe-weighted")
    out = {"families": rep, "entered": list(enter), "reference 2023-26": round(S(ref, JUDGE), 3), "book 2023-26": round(S(book, JUDGE), 3),
           "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > 0.815)
    print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen153.json", "w"), indent=1)
    book.to_frame("book").to_parquet(ROOT / "results/gen153_book.parquet")
