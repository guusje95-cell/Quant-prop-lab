"""Gen182 (config/gen182_protocol.json): F3 weighted to refunding months. Writes results/gen182.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
B3 = ["ZN", "ZB", "ZF"]; R3 = pd.DataFrame({r: D[r].r for r in B3}).sort_index(); SD3 = R3.ewm(span=35, min_periods=30).std()


def f3(mult):
    W = pd.DataFrame(0.0, index=R3.index, columns=B3); k = 3
    for per, gg in R3.index.to_series().groupby(R3.index.to_period("M")):
        if len(gg) < k + 2:
            continue
        m = mult(per.month)
        if m == 0:
            continue
        d0 = gg.index[-(k + 1)]; iv = 1 / SD3.loc[d0]
        if np.isfinite(iv).all():
            W.loc[gg.index[-k:]] = (m * iv / iv.sum() * 3 * 0.003 / SD3.loc[d0].mean()).to_numpy()
    return daily_book(W, B3)


RF = (2, 5, 8, 11)
V = {"flat": lambda m: 1.0, "refund": lambda m: 1.6 if m in RF else 0.7, "refund-only": lambda m: 2.0 if m in RF else 0.0}
res = {}
for n, fn in V.items():
    p = f3(fn); res[n] = (S(p, TUNE), p); print(n, round(res[n][0], 3), round(S(p, JUDGE), 3), flush=True)
ch = max(res, key=lambda k: res[k][0]); out = {"variants": {k: [round(v[0], 3), round(S(v[1], JUDGE), 3)] for k, v in res.items()}, "chosen": ch}
if ch != "flat":
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["F3"] = res[ch][1]
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen182_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen182.json", "w"), indent=1)
