"""Gen143 (config/gen143_protocol.json): nested tuning of other futures families. Writes results/gen143.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read()
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], g)
exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], g)
F, S, TUNE, JUDGE, build, D, daily_book, R24 = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build", "D", "daily_book", "R24"))
SD = R24.ewm(span=35, min_periods=30).std(); ME = R24.index.to_series().groupby(R24.index.to_period("M")).max(); PX = (1 + R24.fillna(0.0)).cumprod()
COM = ["GC", "SI", "HG", "CL", "NG", "RB", "HO", "ZC", "ZS", "ZW", "LE", "HE"]


def xs(score, members, n, high_long=True):
    W = pd.DataFrame(np.nan, index=R24.index, columns=members)
    for d in ME:
        s = score.loc[d, members].dropna() if d in score.index else pd.Series(dtype=float)
        if len(s) < 2 * n:
            continue
        top, bot = (s.nlargest(n).index, s.nsmallest(n).index) if high_long else (s.nsmallest(n).index, s.nlargest(n).index)
        w = pd.Series(0.0, index=members); iv = 1 / SD.loc[d, members]; w[top] = iv[top]; w[bot] = -iv[bot]; W.loc[d] = w / w.abs().sum()
    return daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), members)


def u5(lb, n):
    return xs(PX.shift(21) / PX.shift(lb) - 1, list(R24.columns), n)


R2 = pd.DataFrame({r: F.daily_second(r) for r in COM}).reindex(R24.index)


def h1(lb, n):
    cum = lambda x: (1 + x.fillna(0.0)).rolling(lb, min_periods=lb - 10).apply(np.prod, raw=True) - 1
    return xs(cum(R24[COM]) - cum(R2), COM, n)


fomc = pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date)
fz = F.front("ZN"); tz = F.ny(fz.index); pz = (1 + fz.r).cumprod()
c13 = pz[tz.h == 13].groupby(tz.date[tz.h == 13]).last(); c15 = pz[tz.h == 15].groupby(tz.date[tz.h == 15]).last(); fsig = np.sign(c15 / c13.reindex(c15.index) - 1)
MR = ["ZN", "ZB"]; RR = pd.DataFrame({r: D[r].r for r in MR}).sort_index(); VR = RR.rolling(60).std() * np.sqrt(252)


def f1(hold):
    W = pd.DataFrame(0.0, index=RR.index, columns=MR)
    for d in fomc:
        d = d.normalize()
        if d not in RR.index or d not in fsig.index or not np.isfinite(fsig[d]) or fsig[d] == 0:
            continue
        i = RR.index.get_loc(d)
        for r in MR:
            W.loc[RR.index[i + 1:i + 1 + hold], r] = fsig[d] * 0.10 / VR[r].iloc[i]
    return daily_book(W.fillna(0.0), MR)


es, zn = F.daily("ES"), F.daily("ZN"); RK = pd.DataFrame({"ES": es.r, "ZN": zn.r}).dropna(); VK = RK.ES.rolling(60).std() * np.sqrt(252)


def k3(k):
    W = pd.Series(0.0, index=RK.index)
    for _, gg in RK.groupby(RK.index.to_period("M")):
        if len(gg) < k + 3:
            continue
        d0 = gg.index[-(k + 1)]; mtd = (1 + gg.loc[:d0]).prod() - 1
        W.loc[gg.index[-k:]] = (-1.0 if mtd.ES > mtd.ZN else 1.0) * 0.15 / VK.loc[d0]
    cst = es.cost.reindex(RK.index).ffill(); roll = es.roll.reindex(RK.index).fillna(0); turn = W.diff().abs().fillna(W.abs()) + 2 * W.abs() * roll
    return W * RK.ES - turn * cst


c = {"__file__": str(ROOT / "scripts/gen119_cot.py")}
cs = open(ROOT / "scripts/gen119_cot.py").read(); exec(cs[:cs.index("def contrarian_book")], c)
dis = c["load"]("cot_disagg.parquet", c["DIS"], ["M_Money_Positions_Long_All", "M_Money_Positions_Short_All"])
tff = c["load"]("cot_tff.parquet", c["TFF"], ["Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"])


def cot(rec, cols, thr):
    members = list(rec); R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); vol = R.ewm(span=60, min_periods=40).std() * np.sqrt(252)
    W = pd.DataFrame(0.0, index=R.index, columns=members)
    for r in members:
        x = rec[r]; z = c["zscore"]((x[cols[0]] - x[cols[1]]) / x["Open_Interest_All"], 156, 104)
        s = pd.Series(np.where(z > thr, -1.0, np.where(z < -thr, 1.0, 0.0)), index=z.index)
        W[r] = c["weekly_to_daily"](s, R.index).fillna(0.0) * (0.40 / vol[r]) / len(members)
    return daily_book(W.shift(1).fillna(0.0).where(np.isfinite, 0.0), members)


FAM = {"U5": [(u5, {"lb": lb, "n": n}) for lb in (63, 126, 252) for n in (4, 6)],
       "H1": [(h1, {"lb": lb, "n": n}) for lb in (63, 126, 252) for n in (3, 4)],
       "F1": [(f1, {"hold": h}) for h in (5, 10, 15)], "K3": [(k3, {"k": k}) for k in (2, 3, 5)],
       "C2": [(lambda thr: cot(tff, ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"), thr), {"thr": t}) for t in (1.0, 1.5, 2.0)],
       "C1": [(lambda thr: cot(dis, ("M_Money_Positions_Long_All", "M_Money_Positions_Short_All"), thr), {"thr": t}) for t in (1.0, 1.5, 2.0)]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = [(S(fn(**prm), TUNE), prm, fn(**prm)) for fn, prm in opts]
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
    print(name, rep[name], flush=True)
B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {"F3": g["f3"], "F5": g["f5"], "G1": g["g1"], "P1": g["p1"], "A3": g["a3"]}
base = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
book = build(pd.DataFrame({**base, **enter}), "sharpe-weighted")
out = {"families": rep, "entered": list(enter), "book 2023-26": round(S(book, JUDGE), 3),
       "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)], "reference": 0.661}
out["adopt"] = bool(out["book 2023-26"] > 0.661)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen143.json", "w"), indent=1)
book.to_frame("book").to_parquet(ROOT / "results/gen143_book.parquet"); pd.DataFrame(enter).to_parquet(ROOT / "results/gen143_entrants.parquet")
