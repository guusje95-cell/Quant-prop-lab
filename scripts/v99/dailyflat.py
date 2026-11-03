"""Exact daily-flat execution for futures prop firms that must be flat around the daily close (Topstep / MFFU flat by 16:10 ET,
Tradeify 16:45, Apex 16:59; reopen at 18:00 ET) and over the weekend. Patches futures_db so EVERY sleeve built on it sees:
  - the bar that starts at 16:00 ET: return 0 (position closed at 16:00 ET, conservative vs 16:10)
  - the first bar after a gap (18:00 ET session open, Sunday 18:00 after the weekend): return open -> close only (the gap is not earned)
Costs: set QPL_DAILY_FLAT=1 as well (the sleeves then charge one extra round trip per held day). Use: import dailyflat; dailyflat.patch()
BEFORE any sleeve code runs (futures_db.front / second are cached)."""
import os
from functools import lru_cache

import numpy as np
import pandas as pd


def _fix(f):
    f = f.copy()
    et = pd.DatetimeIndex(f.index).tz_localize("UTC").tz_convert("America/New_York")
    gap = np.r_[np.inf, np.diff(f.index.asi8) / 3.6e12] > 1.01
    first = pd.Series(gap, index=f.index)
    oc = (f["close"] / f["open"] - 1).where((f["open"] > 0) & (f["close"] > 0), 0.0)
    r = f["r"].copy()
    r[first.to_numpy()] = oc[first.to_numpy()]
    if os.environ.get("QPL_FLAT_FROM", "16") == "16":
        r[(et.hour == 16)] = 0.0                                                # futures firms: flat from 16:00 ET (CFD firms: QPL_FLAT_FROM=17)
    f["r"] = r.fillna(0.0)
    return f


def patch():
    import futures_db as F
    if getattr(F, "_dailyflat", False):
        return F
    of, os_ = F.front.__wrapped__, F.second.__wrapped__
    F.front = lru_cache(maxsize=None)(lambda root: _fix(of(root)))
    F.second = lru_cache(maxsize=None)(lambda root: _fix(os_(root)))
    F._dailyflat = True
    return F
