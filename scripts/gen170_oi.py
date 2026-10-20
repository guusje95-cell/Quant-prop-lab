"""Gen170 (config/gen170_protocol.json): open-interest growth, aggregate and cross-section. Writes results/gen170.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
c = {"__file__": str(ROOT / "scripts/gen119_cot.py")}; cs = open(ROOT / "scripts/gen119_cot.py").read(); exec(cs[:cs.index("def contrarian_book")], c)
dis = c["load"]("cot_disagg.parquet", c["DIS"], ["M_Money_Positions_Long_All", "M_Money_Positions_Short_All"])
COM = list(c["DIS"]); OI = pd.DataFrame({r: dis[r]["Open_Interest_All"] for r in COM}).sort_index().astype(float)
R = pd.DataFrame({r: D[r].r for r in COM}).sort_index(); R = R[R.index.weekday < 5]; vol = (R.ewm(span=60, min_periods=40).std() * np.sqrt(252)).shift(1)
wtd = c["weekly_to_daily"]


def oa(L):
    norm = OI / OI.rolling(52, min_periods=40).mean(); agg = norm.mean(axis=1); g = np.log(agg / agg.shift(L))
    on = wtd((g > 0).astype(float), R.index).fillna(0.0)
    W = (0.10 / vol / len(COM)).mul(on, axis=0)
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), COM)


def ox(L):
    g = np.log(OI / OI.shift(L)); rk = g.rank(axis=1)
    n = g.notna().sum(axis=1)
    s = pd.DataFrame(np.where(rk.ge(n - 2, axis=0), 1.0, np.where(rk.le(3, axis=0), -1.0, 0.0)), index=g.index, columns=COM).where(g.notna(), 0.0)
    s = wtd(s, R.index).fillna(0.0)
    W = s * (0.10 / vol) / 6
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), COM)


FAM = {"OA": [(oa, {"L": L}) for L in (4, 13, 52)], "OX": [(ox, {"L": L}) for L in (4, 13, 52)]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen170_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen170.json", "w"), indent=1)
