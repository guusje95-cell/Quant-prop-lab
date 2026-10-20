"""Gen142 (config/gen142_protocol.json): overnight-session drift grid, nested. Writes results/gen142.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen140_optimise.py").read()
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], g)
exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], g)
F, S, TUNE, JUDGE, build = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build"))
FR = {r: F.front(r) for r in ("ES", "NQ", "RTY", "YM")}; ET = {r: F.ny(FR[r].index) for r in FR}


def night(markets, start, end):
    tot = []
    for r in markets:
        f, t = FR[r], ET[r]; h = t.h
        m = ((h >= start) | (h < end)) if start > end else ((h >= start) & (h < end))
        m = m & ~((t.wd == 4) & (h >= 17)) & ~(t.wd == 5)                     # no Friday-evening / Saturday bars
        p = pd.Series(np.where(m, 1.0 / len(markets), 0.0), index=f.index); c = F.cost_frac(r, f.close)
        tot.append(p * f.r - p.diff().abs().fillna(p.abs()) * c - p.abs() * f.roll * 2 * c)
    x = pd.concat(tot, axis=1).fillna(0.0).sum(axis=1); return x.groupby(F.trade_date(x.index)).sum()


res = []
for mk in (("ES", "NQ"), ("ES", "NQ", "RTY", "YM")):
    for s in (18, 20, 22, 0):
        for e in (3, 6, 9):
            p = night(mk, s, e); res.append((S(p, TUNE), {"markets": list(mk), "start": s, "end": e}, p))
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {"F3": g["f3"], "F5": g["f5"], "G1": g["g1"], "P1": g["p1"], "A3": g["a3"]}
base = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
book = build(pd.DataFrame({**base, "night drift": p}), "sharpe-weighted")
out = {"top 5 on 2010-22": [(round(x[0], 3), x[1]) for x in res[:5]], "chosen": prm, "tune 2010-22": round(s, 3),
       "stand-alone 2023-26": round(S(p, JUDGE), 3), "stand-alone 2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)],
       "book with it 2023-26": round(S(book, JUDGE), 3), "reference book": 0.661}
out["(a) stand-alone pass"] = bool(out["stand-alone 2023-26"] >= 0.3); out["(b) adopt into book"] = bool(out["book with it 2023-26"] > 0.661)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen142.json", "w"), indent=1)
p.to_frame("night").to_parquet(ROOT / "results/gen142_daily.parquet")
