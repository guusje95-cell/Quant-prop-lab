"""Intraday feature preparation for US equity-index (and other) bars.

Every feature is computed causally: a value stamped on bar t uses only bars <= t
(inclusive of bar t's close, which is known when bar t ends)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.calendar import early_closes, holidays
from ..data.sessions import RTH_CLOSE_MIN, RTH_OPEN_MIN, cme_trading_date, to_et


def prepare(df: pd.DataFrame, bar_min: int) -> pd.DataFrame:
    """Add session columns. `date` = ET calendar date, `cme_date` = Globex trading date."""
    out = df.copy()
    e = to_et(out.index)
    m = (e.hour * 60 + e.minute).to_numpy()
    out["et_min"] = m
    out["date"] = e.normalize().tz_localize(None)
    out["cme_date"] = cme_trading_date(out.index)
    out["dow"] = e.dayofweek
    hol = holidays()
    ec = early_closes()
    out["holiday"] = out["date"].isin(hol).to_numpy()
    out["early_close"] = out["date"].isin(ec).to_numpy()
    out["rth"] = (m >= RTH_OPEN_MIN) & (m + bar_min <= RTH_CLOSE_MIN)
    out["valid_day"] = (~out["holiday"]) & (~out["early_close"]) & (out["dow"] < 5)
    # RTH bar number within the day (0 = 09:30 bar)
    out["rth_bar"] = np.where(out["rth"], (m - RTH_OPEN_MIN) // bar_min, -1)
    out["last_rth_bar"] = out["rth"] & (m + bar_min == RTH_CLOSE_MIN)
    out["sess"] = (out["date"].astype("int64") // 86_400_000_000_000).astype(np.int64)
    return out


def daily_rth_table(p: pd.DataFrame) -> pd.DataFrame:
    """One row per ET date with RTH open/high/low/close (only complete, valid days)."""
    r = p[p["rth"] & p["valid_day"]]
    g = r.groupby("date")
    t = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "nbars": g.size(),
                      "first_min": g["et_min"].first(), "last_min": g["et_min"].last()})
    return t


def add_prev_close(p: pd.DataFrame, bar_min: int) -> pd.DataFrame:
    """prev_rth_close: close of the last RTH bar of the previous valid day (known before today's open)."""
    t = daily_rth_table(p)
    full = t[(t["first_min"] == RTH_OPEN_MIN) & (t["last_min"] + bar_min == RTH_CLOSE_MIN)]
    prev_close = full["close"].shift(1)
    # map each date to the previous complete day's close (dates without complete data -> NaN)
    pc = pd.Series(prev_close.values, index=full.index)
    p = p.copy()
    p["prev_rth_close"] = p["date"].map(pc)
    day_open = t["open"].where(t["first_min"] == RTH_OPEN_MIN)
    p["rth_open"] = p["date"].map(day_open)
    p["complete_day"] = p["date"].isin(full.index)
    return p


def atr_daily(t: pd.DataFrame, n: int = 14) -> pd.Series:
    """Daily ATR from the RTH table, SHIFTED by one day (known before today's open)."""
    pc = t["close"].shift(1)
    tr = np.maximum(t["high"] - t["low"], np.maximum((t["high"] - pc).abs(), (t["low"] - pc).abs()))
    return tr.rolling(n, min_periods=n).mean().shift(1)


def intraday_cum_from_open(p: pd.DataFrame) -> np.ndarray:
    """|close_t / rth_open - 1| for RTH bars."""
    return np.abs(p["close"].to_numpy() / p["rth_open"].to_numpy() - 1.0)
