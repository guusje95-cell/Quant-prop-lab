"""E2_TREND_BREAKOUT_LO (frozen in gen28, config/crypto_gen28_protocol.json) + gen29 STRESS_CAP overlay.

Daily, decided on completed UTC daily candles (close at 00:00 UTC), executed right after 00:00 UTC:
  per coin: s = 0.5 * mean_{n in 5,7,10,14,20; hold in 1,2,3} short_breakout(n, hold)
              + 0.5 * mean_{n in 14,30,60,90} tsmom(n), clipped at 0 (long-only)
  raw weight w = s * min(1, 0.40 / sigma30) / N   (N = coins with >= 200 daily candles)
  scaled weight = L * w;  STRESS_CAP: if sum(long w * stress) > b, scale all by b / sum
  stress_i = max(0.20, worst-ever (1 - low / previous close) of coin i up to the previous day)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from qpl.strategies import crypto_zoo as Z

SQ = np.sqrt(365)
BO = [(n, k) for n in (5, 7, 10, 14, 20) for k in (1, 2, 3)]
TM = (14, 30, 60, 90)


def signal_one(close: pd.Series, scale: int = 1) -> pd.Series:
    """scale = bars per day (1 = daily bars; 6 = 4h bars with the same calendar horizons)."""
    s = close.dropna()
    bo = sum(Z.short_breakout(s, n * scale, k * scale) for n, k in BO) / len(BO)
    tm = sum(Z.tsmom(s, n * scale) for n in TM) / len(TM)
    return (0.5 * bo.clip(lower=0) + 0.5 * tm.clip(lower=0))


def signals(close: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({a: signal_one(close[a]) for a in close.columns}).reindex_like(close).fillna(0)


def raw_weights(close: pd.DataFrame) -> pd.DataFrame:
    hist = close.notna().cumsum() >= 200
    sig30 = np.log(close).diff().rolling(30, min_periods=20).std() * SQ
    n = hist.sum(axis=1).replace(0, np.nan)
    return (signals(close) * (0.40 / sig30).clip(upper=1.0)).where(hist, 0.0).div(n, axis=0).fillna(0)


def stress(close: pd.DataFrame, low: pd.DataFrame, floor: float = 0.20) -> pd.DataFrame:
    """Known at the close of day t: worst wick up to and including day t (applied to the position held on day t+1)."""
    wick = (1 - low / close.shift(1)).clip(lower=0)
    return wick.cummax().ffill().fillna(floor).clip(lower=floor)


def capped_weights(close, low, L: float, b: float | None) -> pd.DataFrame:
    w = raw_weights(close) * L
    if b is None:
        return w
    load = (w.clip(lower=0) * stress(close, low)).sum(axis=1)
    scale = (b / load).where(load > b, 1.0).fillna(1.0)
    return w.mul(scale, axis=0)


def stable_overlay(stable_cap: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """O3 (gen36/37): USDT+USDC total market cap 30-day log change > 0 -> 1.25, <= 0 -> 0.75, unknown -> 1.0.
    stable_cap is indexed by UTC day (value for that day); applied with a 1-day publication lag."""
    s = stable_cap.reindex(index)
    g = np.log(s.where(s > 0)).diff(30)
    f = pd.Series(np.where(g > 0, 1.25, np.where(g <= 0, 0.75, 1.0)), index=index)
    return f.shift(1).fillna(1.0)
