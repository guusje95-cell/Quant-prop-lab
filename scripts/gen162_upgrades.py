"""Gen162 (config/gen162_protocol.json): F5 trend filter and quarter-end K3. Writes results/gen162.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen143_families.py")}; src = open(ROOT / "scripts/gen143_families.py").read()
exec(src.split("c = {\"__file__\"")[0], g)
F, S, TUNE, JUDGE, D, daily_book, build, RK, VK, es = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book", "build", "RK", "VK", "es"))
E = ["ES", "NQ"]; RE = pd.DataFrame({r: D[r].r for r in E}).sort_index(); PXE = (1 + RE.fillna(0.0)).cumprod()


def f5(filt):
    rv = RE.rolling(20).std() * np.sqrt(252); w = 0.5 * (0.15 / rv).clip(upper=2)
    if filt:
        w = w * (PXE > PXE.rolling(filt).mean())
    return daily_book(w.shift(1).fillna(0.0), E)


def k3q(quarter):
    W = pd.Series(0.0, index=RK.index); k = 5
    for per, gg in RK.groupby(RK.index.to_period("M")):
        if len(gg) < k + 3 or (quarter and per.month not in (3, 6, 9, 12)):
            continue
        d0 = gg.index[-(k + 1)]; mtd = (1 + gg.loc[:d0]).prod() - 1
        W.loc[gg.index[-k:]] = (-1.0 if mtd.ES > mtd.ZN else 1.0) * 0.15 / VK.loc[d0] * (2 if quarter else 1)
    cst = es.cost.reindex(RK.index).ffill(); roll = es.roll.reindex(RK.index).fillna(0); turn = W.diff().abs().fillna(W.abs()) + 2 * W.abs() * roll
    return W * RK.ES - turn * cst


FAM = {"F5": [(f5, {"filt": f}) for f in (0, 200, 100)], "K3": [(k3q, {"quarter": q}) for q in (False, True)]}
CUR = {"F5": {"filt": 0}, "K3": {"quarter": False}}
rep, repl = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3)}
    if prm != CUR[name]:
        repl[name] = p
out = {"families": rep, "replaced": list(repl)}
if repl:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in repl.items():
        base[n] = p
    b = build(base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 0.908)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen162_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen162.json", "w"), indent=1)
