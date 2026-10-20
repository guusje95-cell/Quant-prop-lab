"""Gen218 (config/gen218_protocol.json): 2003-2010 backcast of the adopted equity sleeves on Dukascopy daily CFDs. Writes results/gen218.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from dateutil.easter import easter
from pandas.tseries.holiday import USFederalHolidayCalendar
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "research_data/dukascopy_daily"
A, Z = "2003-06-01", "2010-05-31"
ld = lambda s: pd.read_parquet(RAW / f"{s}_D1_raw.parquet")
E = {"US500": ld("USA500IDXUSD"), "USTECH": ld("USATECHIDXUSD")}
oil = ld("LIGHTCMDUSD").close
IX = E["US500"].index.intersection(E["USTECH"].index); IX = IX[IX.weekday < 5]
hol = set(USFederalHolidayCalendar().holidays("2002-01-01", "2011-12-31")) | {pd.Timestamp(easter(y)) - pd.Timedelta(days=2) for y in range(2002, 2012)}
hol = {d for d in hol if d.weekday() < 5}


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def run(pos_fn):
    out = []
    for n, d in E.items():
        d = d.reindex(IX); r = d.close.pct_change(); w = pos_fn(d).reindex(IX).fillna(0.0)      # w[t] = position held during day t
        out.append(0.5 * (w * r - w.diff().abs().fillna(w.abs()) * 1e-4))
    return pd.concat(out, axis=1).sum(axis=1).loc[A:Z]


def r1d(d):
    c, ibs, r = d.close, (d.close - d.low) / (d.high - d.low), d.close.pct_change()
    ind = [rsi2(c) < 10, c <= c.rolling(5).min(), c.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
    mult = (r.rolling(250, min_periods=120).std() / r.rolling(20).std()).clip(upper=2)
    return (sum(z.astype(float) for z in ind) / 4 * mult).shift(1)


p1d = lambda d: ((d.close - d.low) / (d.high - d.low) < 0.3).astype(float).shift(1)


def mask(fn):
    return lambda d: pd.Series(fn(IX), index=IX)


def t1(ix):
    m = np.zeros(len(ix)); st = np.where(~pd.Series(ix.to_period("M")).duplicated().to_numpy())[0]
    for i in st[1:]:
        m[max(0, i - 2):i + 3] = 1
    return m


def t2(ix):
    m = np.zeros(len(ix))
    for h in hol:
        j = ix.searchsorted(h)
        if 0 < j <= len(ix):
            m[j - 1] = 1
    return m


def mm(ix):
    m = np.zeros(len(ix))
    for _, g in ix.to_series().groupby(ix.to_period("M")):
        d0 = g[g.index.day >= 15]
        if len(d0):
            i = ix.get_loc(d0.index[0]); m[max(i - 1, 0):i + 2] = 1
    return m


def oilm(ix):
    o = oil.reindex(ix).ffill(); s = o / o.shift(21) - 1; me = ix.to_series().groupby(ix.to_period("M")).max()
    pos = pd.Series(np.nan, index=ix)
    for d in me:
        pos.loc[d] = 1.0 if s.loc[d] < 0 else 0.0
    return pos.ffill().shift(1).fillna(0.0).to_numpy()


SL = {"R1d": run(r1d), "P1d": run(p1d), "T1": run(mask(t1)), "T2": run(mask(t2)), "MM": run(mask(mm)), "OIL": run(mask(oilm))}
sh = lambda x: round(float(x.mean() / x.std() * np.sqrt(252)), 3) if x.std() > 0 else None
P = pd.DataFrame(SL); w = 1 / P.std(); w = w / w.sum(); comb = (P * w).sum(axis=1)
bh = pd.concat([E[n].close.reindex(IX).pct_change() for n in E], axis=1).mean(axis=1).loc[A:Z]
out = {"window": [A, Z], "per sleeve": {k: sh(v) for k, v in SL.items()}, "per year (combined)": {str(y): sh(comb.loc[str(y)]) for y in range(2003, 2011)},
       "combined (EQR within window)": sh(comb), "buy-and-hold US500/USTECH": sh(bh)}
out["fragile (negative backcast)"] = [k for k, v in out["per sleeve"].items() if v is not None and v < 0]
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen218.json", "w"), indent=1)
