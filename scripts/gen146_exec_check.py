"""Gen146 execution check of R1: signal and fill at an intraday snapshot (ET hour), 24h hold. Writes results/gen146_exec.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen146_equity.py")}; exec(open(ROOT / "scripts/gen146_equity.py").read().split("if __name__")[0], g)
F, S, TUNE, JUDGE, EQ, rsi2 = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "EQ", "rsi2")); D = {r: F.daily(r) for r in EQ}


def snap_book(hour, th=10):
    out = {}
    for r in EQ:
        f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod()
        wk = t.wd < 5; rth = wk & (t.h >= 9) & (t.h < hour)
        c = pz[wk & (t.h == hour - 1)].groupby(t.date[wk & (t.h == hour - 1)]).last()       # close of the bar ending at `hour`:00 ET
        hi = pz[rth].groupby(t.date[rth]).max(); lo = pz[rth].groupby(t.date[rth]).min()
        hi, lo = hi.reindex(c.index), lo.reindex(c.index); hi = np.maximum(hi, c); lo = np.minimum(lo, c)
        ibs = (c - lo) / (hi - lo)
        ind = [(rsi2(c) < th), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
        sig = (sum(x.astype(float) for x in ind) / 4).where(hi > lo, 0.0)
        ret = c.shift(-1) / c - 1; ret[(c.index.to_series().diff(-1).dt.days < -4).to_numpy()] = np.nan   # skip gaps > 4 days
        cost = D[r].cost.reindex(c.index).ffill(); w = 0.25 * sig
        out[r] = (w * ret - w.diff().abs().fillna(w) * cost).shift(1)                       # pnl dated on the exit day
    p = pd.DataFrame(out).sum(axis=1)
    return p[p.index.weekday < 5]


res = {}
for h in (12, 14, 15, 16):
    p = snap_book(h); res[f"{h}:00 ET"] = {"2010-22": round(S(p, TUNE), 3), "2023-26": round(S(p, JUDGE), 3)}
    print(h, res[f"{h}:00 ET"], flush=True)
json.dump(res, open(ROOT / "results/gen146_exec.json", "w"), indent=1)

# book with the executable R1 (14:00 ET) in place of the close-fill R1
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {k: h[k.lower()] for k in ("F3", "F5", "G1", "P1", "A3")}
b0 = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
e143 = pd.read_parquet(ROOT / "results/gen143_entrants.parquet"); s146 = pd.read_parquet(ROOT / "results/gen146_sleeves.parquet")
P = pd.DataFrame({**b0, **{c: e143[c] for c in e143}, "R1": snap_book(14), "T1": s146["T1"], "T2": s146["T2"]})
book = h["build"](P, "sharpe-weighted")
res["book with R1 at 14:00 ET"] = {"2010-17": round(F.sharpe(book, *F.SPLITS[0]), 3), "2018-22": round(F.sharpe(book, *F.SPLITS[1]), 3), "2023-26": round(S(book, JUDGE), 3)}
print(res["book with R1 at 14:00 ET"])
json.dump(res, open(ROOT / "results/gen146_exec.json", "w"), indent=1)
book.to_frame("book").to_parquet(ROOT / "results/gen146_book_exec.parquet")
