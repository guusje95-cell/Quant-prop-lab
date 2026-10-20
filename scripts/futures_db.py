"""Databento CME hourly loader for Gen114/115: roll-safe returns, contract specs, costs, New York clock.

research_data/databento/{ROOT}_1h.parquet: ts_event (UTC bar start), symbol (ROOT.v.0 front / ROOT.v.1 second), OHLCV, instrument_id.
Returns are computed within one instrument_id only: at a roll bar the new front's previous close is taken from the bar
where that same contract was the second contract, so roll jumps never become P&L."""
import os
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("QPL_DATABENTO", ROOT / "research_data" / "databento"))
END = "2026-09-30 23:00"
# root: (tick size, full multiplier, micro multiplier or None, fixed roll spacing in years, asset class)
SPEC = {"ES": (0.25, 50, 5, .25, "equity"), "NQ": (0.25, 20, 2, .25, "equity"), "RTY": (0.1, 50, 5, .25, "equity"), "YM": (1.0, 5, 0.5, .25, "equity"),
        "ZN": (1 / 64, 1000, None, .25, "rates"), "ZB": (1 / 32, 1000, None, .25, "rates"), "ZF": (1 / 128, 1000, None, .25, "rates"), "ZT": (1 / 256, 2000, None, .25, "rates"),
        "6E": (5e-5, 125000, 12500, .25, "fx"), "6J": (5e-7, 12.5e6, 1.25e6, .25, "fx"), "6B": (1e-4, 62500, 6250, .25, "fx"), "6A": (5e-5, 100000, 10000, .25, "fx"),
        "6C": (5e-5, 100000, 10000, .25, "fx"), "6S": (5e-5, 125000, None, .25, "fx"),
        "GC": (0.1, 100, 10, 1 / 6, "metal"), "SI": (0.005, 5000, 1000, 1 / 6, "metal"), "HG": (5e-4, 25000, 2500, 1 / 6, "metal"),
        "CL": (0.01, 1000, 100, 1 / 12, "energy"), "NG": (1e-3, 10000, 1000, 1 / 12, "energy"), "RB": (1e-4, 42000, None, 1 / 12, "energy"), "HO": (1e-4, 42000, None, 1 / 12, "energy"),
        "ZC": (0.25, 50, 5, 1 / 6, "ags"), "ZS": (0.25, 50, 5, 1 / 6, "ags"), "ZW": (0.25, 50, 5, 1 / 6, "ags"), "LE": (0.025, 400, None, 1 / 6, "ags"), "HE": (0.025, 400, None, 1 / 6, "ags"),
        "BZ": (0.01, 1000, None, 1 / 12, "energy"),
        "BTC": (5.0, 5, 0.1, 1 / 12, "crypto"), "ETH": (0.5, 50, 0.1, 1 / 12, "crypto")}
NONCRYPTO = [r for r in SPEC if SPEC[r][4] != "crypto" and r != "BZ"]          # BZ (Brent, Gen128) is not in the 24-market set
COMMISSION = {"micro": 0.85, "full": 2.50}                    # $ per side per contract, incl. exchange fees (assumption)


@lru_cache(maxsize=None)
def raw(root):
    d = pd.read_parquet(DB / f"{root}_1h.parquet")
    d["ts"] = pd.to_datetime(d["ts_event"], utc=True).dt.tz_localize(None)
    d = d[d["ts"] <= pd.Timestamp(END)]
    return d.sort_values("ts")


@lru_cache(maxsize=None)
def front(root):
    """Front-contract hourly bars with a roll-safe return column `r` (move during the bar, bar-start label) and the second
    contract's close `close2` at the same bar."""
    d = raw(root)
    f = d[d.symbol.str.endswith(".v.0")].drop_duplicates("ts").set_index("ts")
    s = d[d.symbol.str.endswith(".v.1")].drop_duplicates("ts").set_index("ts")
    last = d.drop_duplicates(["ts", "instrument_id"]).set_index(["instrument_id", "ts"])["close"]
    prev_ts = pd.Series(f.index, index=f.index).shift(1)
    prev_id = f.instrument_id.shift(1)
    same = f.instrument_id.eq(prev_id)
    prev_close = f.close.shift(1).where(same)
    r = (f.close / prev_close - 1).where(same)
    roll = ~same & prev_ts.notna()
    if roll.any():                                            # roll bar: the contract we HELD (old front) over the bar, else the
        ro = roll[roll].index                                 # new front's own previous close at the previous bar, else 0
        old_now = last.reindex(list(zip(prev_id[ro].astype("int64"), ro))).to_numpy()
        old_prev = f.close.shift(1)[ro].to_numpy()
        new_prev = last.reindex(list(zip(f.instrument_id[ro], prev_ts[ro]))).to_numpy()
        r_old = old_now / old_prev - 1; r_new = f.close[ro].to_numpy() / new_prev - 1
        r[ro] = np.where(np.isfinite(r_old), r_old, r_new)
    bad = (f.close <= 0) | (f.close.shift(1) <= 0)            # CL April 2020: negative prices, no percentage return
    f["r"] = r.where(~bad).fillna(0.0)
    f["roll"] = roll.astype(int)
    f["close2"] = s.close.reindex(f.index)
    # carry ratio near/far: Databento's volume-ranked .v.1 is sometimes the EXPIRING contract (right after a roll), so the two
    # contracts are ordered by first appearance in the data (listing order = expiry order) instead of by their v.0/v.1 label
    first = d.groupby("instrument_id").ts.min()
    id1 = s.instrument_id.reindex(f.index)
    later = first.reindex(id1).to_numpy() > first.reindex(f.instrument_id).to_numpy()
    f["near_far"] = np.where(later, f.close / f.close2, f.close2 / f.close)
    return f


def cost_frac(root, price):
    """Cost per side as a fraction of notional: one tick of slippage + commission on the micro (or full) contract."""
    tick, mult, micro, _, _ = SPEC[root]
    m = micro or mult; c = COMMISSION["micro" if micro else "full"]
    return tick / price + c / (price * m)


def ny(index):
    et = pd.DatetimeIndex(index).tz_localize("UTC").tz_convert("America/New_York")
    return pd.DataFrame({"h": et.hour, "wd": et.weekday, "date": pd.DatetimeIndex(et.date)}, index=index)


def trade_date(index):
    """CME trading date: bars from 21:00 UTC belong to the next day's session (daily close = last bar before 21:00 UTC)."""
    return (pd.DatetimeIndex(index) + pd.Timedelta(hours=3)).normalize()


def daily(root):
    """Daily roll-safe returns, front/second closes at the daily close, roll flags and cost fraction, indexed by trade date."""
    f = front(root); td = trade_date(f.index)
    g = f.groupby(td)
    out = pd.DataFrame({"r": g.r.apply(lambda x: float(np.prod(1 + x) - 1)), "close": g.close.last(), "close2": g.close2.last(), "near_far": g.near_far.last(),
                        "roll": g.roll.max()})
    out = out[out.index.weekday < 5]
    out["cost"] = cost_frac(root, out.close)
    return out


def sharpe(pnl, a, b):
    x = pnl.loc[a:b]; x = x[x.index.weekday < 5]
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else float("nan")


SPLITS = (("2010-06-01", "2017-12-31"), ("2018-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30"))


def splits(pnl):
    return tuple(round(sharpe(pnl, a, b), 3) for a, b in SPLITS)


def passes(k):
    return bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3)
