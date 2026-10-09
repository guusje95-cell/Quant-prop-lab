"""V6 futures factor signals (config/v6_futures_protocol.json). Every signal at row t uses data through row t only.
Inputs are wide DataFrames (dates x instruments). Output in [-1, 1]; NaN = no view / not eligible."""
from __future__ import annotations

import numba
import numpy as np
import pandas as pd

from ..backtesting.panel import sigma


def logp(ret: pd.DataFrame) -> pd.DataFrame:
    """Log total-return index from percentage returns (NaN-safe: flat on missing days, NaN before first obs)."""
    lp = np.log1p(ret.fillna(0.0)).cumsum()
    return lp.where(ret.notna().cumsum() > 0)


def tsmom(ret, lookbacks=(63, 126, 252)):
    lp = logp(ret)
    parts = [np.sign(lp - lp.shift(L)) for L in lookbacks]
    return sum(parts) / len(parts)


@numba.njit(cache=True)
def _donch(c, n, x):
    T, K = c.shape
    out = np.full((T, K), np.nan)
    for k in range(K):
        cur = 0.0
        for t in range(T):
            if np.isnan(c[t, k]) or t < n:
                continue
            hi = -np.inf; lo = np.inf; ok = True
            for j in range(t - n, t):
                v = c[j, k]
                if np.isnan(v):
                    ok = False; break
                hi = max(hi, v); lo = min(lo, v)
            if not ok:
                continue
            xh = -np.inf; xl = np.inf
            for j in range(t - x, t):
                xh = max(xh, c[j, k]); xl = min(xl, c[j, k])
            if cur == 0.0:
                if c[t, k] > hi:
                    cur = 1.0
                elif c[t, k] < lo:
                    cur = -1.0
            elif cur == 1.0 and c[t, k] < xl:
                cur = 0.0
            elif cur == -1.0 and c[t, k] > xh:
                cur = 0.0
            out[t, k] = cur
    return out


def donchian(ret, n):
    lp = logp(ret)
    return pd.DataFrame(_donch(lp.to_numpy(), n, max(2, n // 2)), index=ret.index, columns=ret.columns)


def ct1_transfer(ret, legs=("t20", "t60", "t120", "d20", "d55")):
    parts = []
    for g in legs:
        parts.append(tsmom(ret, (int(g[1:]),)) if g[0] == "t" else donchian(ret, int(g[1:])))
    return sum(p.fillna(0) for p in parts).div(len(parts)).where(ret.notna().cumsum() > 0)


def ewmac(ret, speeds=((8, 32), (16, 64), (32, 128), (64, 256))):
    lp = logp(ret)
    vol_d = ret.ewm(span=35, min_periods=20, ignore_na=True).std()        # daily return vol (log-index units)
    parts = []
    for f, s in speeds:
        raw = (lp.ewm(span=f, min_periods=f).mean() - lp.ewm(span=s, min_periods=s).mean()) / vol_d
        scale = raw.abs().expanding(min_periods=256).mean()                # scalar learnt from the past only
        parts.append((raw / scale).clip(-2, 2) / 2)
    return sum(parts) / len(parts)


def carry(ret, carry_yield, smooth=21):
    sg = sigma(ret)
    raw = (carry_yield.reindex_like(ret) / sg).rolling(smooth, min_periods=max(1, smooth // 2)).mean()
    scale = raw.abs().rolling(1280, min_periods=256).mean()
    return (raw / scale).clip(-2, 2) / 2


def _xs_rank(score: pd.DataFrame, classes: pd.Series, min_members: int = 4) -> pd.DataFrame:
    out = pd.DataFrame(np.nan, index=score.index, columns=score.columns)
    for cl, cols in classes.groupby(classes).groups.items():
        cols = [c for c in cols if c in score.columns]
        if len(cols) < min_members:
            continue
        sub = score[cols]
        cnt = sub.notna().sum(axis=1)
        pct = sub.rank(axis=1, pct=True)
        sig = pd.DataFrame(np.where(pct > 2 / 3, 1.0, np.where(pct <= 1 / 3, -1.0, 0.0)), index=sub.index, columns=cols)
        sig = sig.where(sub.notna()).where(cnt >= min_members, np.nan)
        out[cols] = sig
    return out


def xs_momentum(ret, classes, lookback=252, skip=21):
    lp = logp(ret)
    score = (lp.shift(skip) - lp.shift(lookback)) / sigma(ret)
    return _xs_rank(score, classes)


def xs_value(ret, classes, start=1260, end=252):
    lp = logp(ret)
    score = -(lp.shift(end) - lp.shift(start))
    return _xs_rank(score, classes)


def xs_skew(ret, classes, window=252):
    score = -ret.rolling(window, min_periods=int(window * 0.8)).skew()
    return _xs_rank(score, classes)


def long_rp(ret):
    return pd.DataFrame(1.0, index=ret.index, columns=ret.columns).where(ret.notna().cumsum() > 0)
