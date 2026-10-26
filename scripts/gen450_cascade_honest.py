"""Gen450 (config/gen450_protocol.json, FLAGGED): survivorship-free cascade variants for v9.6. Writes results/gen450.json and results/gen450_books.parquet."""
import json
import sys
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen57_cascade_hourly as CH
import listing_live as LL
import pit_universe as PU
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
def plan(b, N=1800):
    d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std()
    return round(float((sr - np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e)))) * np.sqrt(365)), 3)
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls})
pack_frames = {c: CH.hourly(c).copy() for c in PU.PACK}
first_bar = {}
def cascade_on(n, min_age=0):
    mem = PU.members(n); CH.CACHE.clear()
    for c in [c for c in mem.columns if mem[c].any()]:
        d = PU.frame(c)
        if d is None:
            continue
        m = mem[c].reindex(d.index.floor("D")).fillna(False).to_numpy()
        if min_age:
            q = PU._qv_daily()[c]; t0 = q.first_valid_index(); m = m & (d.index >= t0 + pd.Timedelta(days=min_age))
        d = d.copy(); d["oi"] = d["oi"].where(m); CH.CACHE[c] = d
    s = CS.cascade(limit=0.005, through=0.001, coins=list(CH.CACHE)).reindex(idx).fillna(0.0)
    CH.CACHE.clear(); CH.CACHE.update(pack_frames); return s
books = {"v9.6 (pack cascade, survivorship-inflated)": unit(CS.portfolio_v5(V6)[0])}
S = {"A point-in-time top-20 cascade": cascade_on(20), "C top-20 listed >= 365 days": cascade_on(20, 365), "D top-10 listed >= 365 days": cascade_on(10, 365)}
for k, s in S.items():
    books[k] = unit(CS.portfolio_v5(V6.assign(**{"cascade limit strict": s}))[0])
books["B no cascade"] = unit(CS.portfolio_v5(V6.drop(columns="cascade limit strict"))[0])
out = {"sleeves": {k: per(s) for k, s in S.items()}, "books": {k: {"book": [shp(b), per(b)], "planning N=1800": plan(b)} for k, b in books.items()}}
pd.DataFrame(books).to_parquet(ROOT / "results/gen450_books.parquet")
(ROOT / "results/gen450.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
