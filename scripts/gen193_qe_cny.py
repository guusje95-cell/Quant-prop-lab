"""Gen193 (config/gen193_protocol.json): quarter-end USD demand and post-CNY copper. Writes results/gen193.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
CNY = pd.to_datetime(["2010-02-14", "2011-02-03", "2012-01-23", "2013-02-10", "2014-01-31", "2015-02-19", "2016-02-08", "2017-01-28", "2018-02-16",
                      "2019-02-05", "2020-01-25", "2021-02-12", "2022-02-01", "2023-01-22", "2024-02-10", "2025-01-29", "2026-02-17"])


def book(members, mask_fn, sign):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); R = R[R.index.weekday < 5]
    v = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1); m = mask_fn(R.index)
    return daily_book((sign * 0.10 / v / len(members)).mul(m, axis=0).fillna(0.0).where(np.isfinite, 0.0), members)


def qd(ix):
    m = pd.Series(0.0, index=ix)
    for per, gg in ix.to_series().groupby(ix.to_period("M")):
        if per.month in (3, 6, 9, 12):
            m.loc[gg.index[-5:]] = 1.0
    return m


def cny(ix):
    m = pd.Series(0.0, index=ix)
    for d in CNY:
        j = ix.searchsorted(d); m.iloc[j:j + 15] = 1.0
    return m


FAM = {"QD": book(["6E", "6J", "6B", "6A", "6C", "6S"], qd, -1.0), "CNY": book(["HG"], cny, 1.0)}
rep, enter = {}, {}
for n, p in FAM.items():
    s = S(p, TUNE); rep[n] = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
    print(n, rep[n], flush=True)
    if s > 0.3:
        enter[n] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    out.update(B.judge(enter, "gen193"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen193.json", "w"), indent=1)
