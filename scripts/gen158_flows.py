"""Gen158 (config/gen158_protocol.json): gotobi Tokyo fix on 6J and mid-month coupon reinvestment. Writes results/gen158.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))

# gotobi days (Tokyo calendar dates)
days = pd.date_range("2010-01-01", "2026-12-31")
bd = days[days.weekday < 5]
got = set()
for d in days:
    last_bd = bd[(bd.year == d.year) & (bd.month == d.month)].max()
    if d.day in (5, 10, 15, 20, 25, 30) or d == last_bd:
        x = d
        while x.weekday() >= 5:
            x -= pd.Timedelta(days=1)
        got.add(x)
fj = F.front("6J"); rj = fj.r.astype(float).fillna(0.0); ix = fj.index
cj = F.cost_frac("6J", fj.close.astype(float))
volj = (rj.groupby(ix.floor("D")).sum().rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
# the fix bar is 00:00-01:00 UTC on the Tokyo date; bars with start hour >= s on the previous UTC date belong to that Tokyo date
tokyo_date = (ix + pd.Timedelta(hours=9)).floor("D")


def gotobi(s, rev):
    hr = ix.hour; on = tokyo_date.isin(list(got))
    pre = on & ((hr >= s) | (hr < 1)); post = on & (hr >= 1) & (hr < 4) & rev
    sz = (0.10 / volj.reindex(ix.floor("D")).to_numpy())
    w = pd.Series(np.where(pre, -1.0, np.where(post, 1.0, 0.0)) * sz, index=ix).fillna(0.0)
    p = w * rj - w.diff().abs().fillna(0.0) * cj
    out = p.groupby(F.trade_date(ix)).sum(); return out[out.index.weekday < 5]


B3 = ["ZF", "ZN", "ZB"]; R3 = pd.DataFrame({r: D[r].r for r in B3}).sort_index(); SD3 = R3.ewm(span=35, min_periods=30).std()


def coupon(k, refund):
    W = pd.DataFrame(0.0, index=R3.index, columns=B3)
    for (y, m), gg in R3.index.to_series().groupby([R3.index.year, R3.index.month]):
        if refund and m not in (2, 5, 8, 11):
            continue
        pre = gg[gg.index.day < 15]
        if len(pre) < k + 2:
            continue
        d0 = R3.index[R3.index.get_loc(pre.index[-k]) - 1]; iv = 1 / SD3.loc[d0]
        if np.isfinite(iv).all():
            W.loc[pre.index[-k:]] = (iv / iv.sum() * 3 * 0.003 / SD3.loc[d0].mean()).to_numpy()
    return daily_book(W, B3)


FAM = {"GB": [(gotobi, {"s": s, "rev": False}) for s in (21, 22, 23)] + [(gotobi, {"s": 22, "rev": True})],
       "MC": [(coupon, {"k": k, "refund": r}) for k in (2, 3, 5) for r in (True, False)]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for k, v in enter.items():
        base[k] = v
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 0.842)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen158_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen158.json", "w"), indent=1)
