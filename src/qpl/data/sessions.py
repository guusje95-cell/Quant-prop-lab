"""Exchange-session helpers. All inputs are UTC-indexed; conversions handle DST
through the IANA tz database (America/New_York), so the US cash open is
always 09:30 ET regardless of daylight-saving transitions (including the
2-3 week windows each year where US and EU DST are misaligned)."""
from __future__ import annotations

import numpy as np
import pandas as pd

ET = "America/New_York"


def to_et(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_convert(ET)


def et_minutes(idx: pd.DatetimeIndex) -> np.ndarray:
    """Minutes since ET midnight of each bar OPEN timestamp."""
    e = to_et(idx)
    return (e.hour * 60 + e.minute).to_numpy()


def et_date(idx: pd.DatetimeIndex) -> np.ndarray:
    """Calendar date in ET (for RTH-based daily grouping)."""
    return to_et(idx).normalize().tz_localize(None).to_numpy()


def cme_trading_date(idx: pd.DatetimeIndex) -> np.ndarray:
    """CME Globex trading date: bars opening at/after 18:00 ET belong to the next
    calendar day's session (Sunday evening -> Monday)."""
    e = to_et(idx)
    d = e.normalize().tz_localize(None)
    roll = np.asarray(e.hour >= 18)
    out = d.to_numpy().copy()
    out[roll] = (d[roll] + pd.Timedelta(days=1)).to_numpy()
    # Friday 18:00+ does not exist on Globex; Saturday sessions never occur.
    return out


RTH_OPEN_MIN = 9 * 60 + 30   # 09:30 ET
RTH_CLOSE_MIN = 16 * 60      # 16:00 ET
TOPSTEP_FLAT_MIN = 16 * 60 + 8   # 15:08 CT == 16:08 ET: Topstep risk desk flattens from 3:08-3:10 PM CT


def rth_mask(idx: pd.DatetimeIndex, bar_minutes: int) -> np.ndarray:
    """True for bars that lie entirely inside 09:30-16:00 ET."""
    m = et_minutes(idx)
    return (m >= RTH_OPEN_MIN) & (m + bar_minutes <= RTH_CLOSE_MIN)
