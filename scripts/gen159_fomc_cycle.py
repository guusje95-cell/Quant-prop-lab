"""Gen159 (config/gen159_protocol.json): FOMC-cycle even weeks and mid-month flow on equity index futures. Writes results/gen159.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
EQ = ["ES", "NQ", "RTY", "YM"]; IX = pd.DataFrame({r: D[r].r for r in EQ}).sort_index().index; IX = IX[IX.weekday < 5]
fomc = sorted(pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date).dt.normalize())
fpos = [IX.searchsorted(d) for d in fomc]
WEEKS = {0: (-1, 3), 2: (9, 13), 4: (19, 23), 6: (29, 33)}


def mask_fc(weeks):
    m = np.zeros(len(IX), bool)
    for k, i in enumerate(fpos):
        nxt = fpos[k + 1] if k + 1 < len(fpos) else len(IX)
        for wk in weeks:
            a, b = WEEKS[wk]
            lo, hi = i + a, min(i + b, nxt - 2 if wk else i + b)      # do not run into the next meeting's week 0
            if lo <= hi:
                m[max(lo, 0):min(hi, len(IX) - 1) + 1] = True
    return m


def mask_mm(a, b):
    m = np.zeros(len(IX), bool)
    for (y, mo), g in IX.to_series().groupby([IX.year, IX.month]):
        d0 = g[g.index.day >= 15]
        if len(d0):
            i = IX.get_loc(d0.index[0]); m[max(i + a, 0):i + b + 1] = True
    return m


def sleeve(m):
    s = pd.Series(m.astype(float), index=IX)
    return daily_book(pd.DataFrame({r: s * 0.25 for r in EQ}), EQ)


FAM = {"FC": [(lambda w: sleeve(mask_fc(w)), {"w": w}) for w in ((0, 2, 4, 6), (0,), (2, 4, 6))],
       "MM": [(lambda a, b: sleeve(mask_mm(a, b)), {"a": a, "b": b}) for a, b in ((-1, 1), (-2, 2))]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(**prm); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": {k: str(v) for k, v in prm.items()}, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
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
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen159_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen159.json", "w"), indent=1)
