"""Intraday feature preparation for US equity-index (and other) bars.

Every feature is computed causally: a value stamped on bar t uses only bars <= t
(inclusive of bar t's close, which is known when bar t ends)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.calendar import early_closes, holidays
from ..data.sessions import RTH_CLOSE_MIN, RTH_OPEN_MIN, cme_trading_date, to_et


def day_ordinal(dates) -> np.ndarray:
    """Unit-safe integer day number (pandas 3 uses microsecond datetimes)."""
    return np.asarray(dates).astype("datetime64[D]").astype(np.int64)


def prepare(df: pd.DataFrame, bar_min: int, open_min: int = RTH_OPEN_MIN, close_min: int = RTH_CLOSE_MIN) -> pd.DataFrame:
    """Add session columns (primary session = [open_min, close_min) ET; default US equity RTH). `date` = ET calendar date, `cme_date` = Globex trading date."""
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
    out["rth"] = (m >= open_min) & (m + bar_min <= close_min)
    out["valid_day"] = (~out["holiday"]) & (~out["early_close"]) & (out["dow"] < 5)
    # RTH bar number within the day (0 = 09:30 bar)
    out["rth_bar"] = np.where(out["rth"], (m - open_min) // bar_min, -1)
    out["last_rth_bar"] = out["rth"] & (m + bar_min == close_min)
    out.attrs["open_min"], out.attrs["close_min"] = open_min, close_min
    out["sess"] = day_ordinal(out["date"].to_numpy())
    return out


def daily_rth_table(p: pd.DataFrame) -> pd.DataFrame:
    """One row per ET date with RTH open/high/low/close (only complete, valid days)."""
    r = p[p["rth"] & p["valid_day"]]
    g = r.groupby("date")
    t = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "nbars": g.size(),
                      "first_min": g["et_min"].first(), "last_min": g["et_min"].last()})
    return t


def asof_prior(day_values: pd.Series, dates) -> np.ndarray:
    """For each date D return the value of `day_values` from the last day STRICTLY before D.
    `day_values[d]` must be computable at the end of day d. Leakage-safe for any D, including
    days whose own data is missing or incomplete."""
    v = day_values.dropna()
    keys = v.index.to_numpy().astype("datetime64[D]")
    q = np.asarray(dates).astype("datetime64[D]")
    pos = np.searchsorted(keys, q, side="left") - 1
    out = np.full(len(q), np.nan)
    ok = pos >= 0
    out[ok] = v.to_numpy()[pos[ok]]
    return out


def add_prev_close(p: pd.DataFrame, bar_min: int) -> pd.DataFrame:
    """prev_rth_close: close of the most recent COMPLETE RTH day strictly before today.
    rth_open: open of today's 09:30 bar, only visible from 09:30 onwards."""
    t = daily_rth_table(p)
    om, cm = p.attrs.get("open_min", RTH_OPEN_MIN), p.attrs.get("close_min", RTH_CLOSE_MIN)
    full = t[(t["first_min"] == om) & (t["last_min"] + bar_min == cm)]
    p = p.copy()
    p["prev_rth_close"] = asof_prior(full["close"], p["date"].to_numpy())
    day_open = t["open"].where(t["first_min"] == om)
    ro = p["date"].map(day_open).to_numpy(dtype=float).copy()
    ro[p["et_min"].to_numpy() < om] = np.nan
    p["rth_open"] = ro
    return p


def atr_series(t: pd.DataFrame, n: int = 14) -> pd.Series:
    """Daily ATR through day d (uses days <= d). Map with asof_prior for use on day d+1."""
    pc = t["close"].shift(1)
    tr = np.maximum(t["high"] - t["low"], np.maximum((t["high"] - pc).abs(), (t["low"] - pc).abs()))
    return tr.rolling(n, min_periods=n).mean()


def intraday_cum_from_open(p: pd.DataFrame) -> np.ndarray:
    """|close_t / rth_open - 1| for RTH bars."""
    return np.abs(p["close"].to_numpy() / p["rth_open"].to_numpy() - 1.0)
