"""Gen26 crypto strategy zoo (config/crypto_zoo_protocol.json). Every function maps a close series (or OHLC frame) to a
signal s_t in [-1, 1] using data through t only. Long-only variants are obtained by clipping at 0."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _state(entry_long, entry_short, exit_long, exit_short) -> np.ndarray:
    el, es, xl, xs = (np.asarray(x, bool) for x in (entry_long, entry_short, exit_long, exit_short))
    out = np.zeros(len(el)); cur = 0.0
    for t in range(len(el)):
        if cur == 0:
            cur = 1.0 if el[t] else (-1.0 if es[t] else 0.0)
        elif cur == 1 and (xl[t] or es[t]):
            cur = -1.0 if es[t] else 0.0
        elif cur == -1 and (xs[t] or el[t]):
            cur = 1.0 if el[t] else 0.0
        out[t] = cur
    return out


def sma_cross(c, f, s):
    return np.sign(c.rolling(f).mean() - c.rolling(s).mean()).fillna(0)


def ema_cross(c, f, s):
    return np.sign(c.ewm(span=f, min_periods=f).mean() - c.ewm(span=s, min_periods=s).mean()).fillna(0)


def price_above_sma(c, n):
    return np.sign(c - c.rolling(n).mean()).fillna(0)


def tsmom(c, n):
    return np.sign(np.log(c).diff(n)).fillna(0)


def donchian_close(c, n):
    hi, lo = c.rolling(n).max().shift(1), c.rolling(n).min().shift(1)
    x = max(2, n // 2)
    xhi, xlo = c.rolling(x).max().shift(1), c.rolling(x).min().shift(1)
    return pd.Series(_state(c > hi, c < lo, c < xlo, c > xhi), index=c.index)


def boll_breakout(c, n, k):
    m, sd = c.rolling(n).mean(), c.rolling(n).std()
    return pd.Series(_state(c > m + k * sd, c < m - k * sd, c < m, c > m), index=c.index)


def boll_reversion(c, n, k):
    m, sd = c.rolling(n).mean(), c.rolling(n).std()
    return pd.Series(_state(c < m - k * sd, c > m + k * sd, c > m, c < m), index=c.index)


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def rsi_reversion(c, n, lo, hi):
    r = rsi(c, n)
    if n == 2:                                            # Connors RSI(2): longs only above SMA200, shorts only below
        trend = c > c.rolling(200).mean()
        return pd.Series(_state((r < lo) & trend, (r > hi) & ~trend, r > 70, r < 30), index=c.index)
    return pd.Series(_state(r < lo, r > hi, r > 50, r < 50), index=c.index)


def rsi_momentum(c, n, up, dn):
    r = rsi(c, n)
    return pd.Series(_state(r > up, r < dn, r < 50, r > 50), index=c.index)


def macd(c, f, s, g):
    m = c.ewm(span=f, min_periods=f).mean() - c.ewm(span=s, min_periods=s).mean()
    return np.sign(m - m.ewm(span=g, min_periods=g).mean()).fillna(0)


def zscore_reversion(c, n, k, hold=3):
    r = np.log(c).diff(n)
    z = (r - r.rolling(250, min_periods=120).mean()) / r.rolling(250, min_periods=120).std()
    trig = pd.Series(np.where(z > k, -1.0, np.where(z < -k, 1.0, 0.0)), index=c.index)
    return trig.replace(0, np.nan).ffill(limit=hold - 1).fillna(0)


def short_breakout(c, n, hold):
    trig = pd.Series(np.where(c > c.rolling(n).max().shift(1), 1.0, np.where(c < c.rolling(n).min().shift(1), -1.0, 0.0)), index=c.index)
    return trig if hold <= 1 else trig.replace(0, np.nan).ffill(limit=hold - 1).fillna(0)


def vol_managed_long(c, n):
    v = np.log(c).diff().rolling(n).var()
    w = (v.rolling(365, min_periods=180).median() / v).clip(upper=2.0) / 2.0
    return w.fillna(0)


def supertrend(df, n, m):
    h, l, c = df.high, df.low, df.close
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, min_periods=n).mean()
    mid = (h + l) / 2
    ub, lb = (mid + m * atr).to_numpy(), (mid - m * atr).to_numpy(); cv = c.to_numpy()
    fu, fl = ub.copy(), lb.copy(); d = np.zeros(len(c)); cur = 1.0
    for t in range(1, len(c)):
        if not np.isfinite(ub[t]):
            continue
        fu[t] = ub[t] if (not np.isfinite(fu[t - 1]) or ub[t] < fu[t - 1] or cv[t - 1] > fu[t - 1]) else fu[t - 1]
        fl[t] = lb[t] if (not np.isfinite(fl[t - 1]) or lb[t] > fl[t - 1] or cv[t - 1] < fl[t - 1]) else fl[t - 1]
        if cur == 1 and cv[t] < fl[t]:
            cur = -1.0
        elif cur == -1 and cv[t] > fu[t]:
            cur = 1.0
        d[t] = cur
    return pd.Series(d, index=c.index)


def ichimoku(df, a, b, s):
    h, l, c = df.high, df.low, df.close
    ten = (h.rolling(a).max() + l.rolling(a).min()) / 2; kij = (h.rolling(b).max() + l.rolling(b).min()) / 2
    spa = ((ten + kij) / 2).shift(b); spb = ((h.rolling(s).max() + l.rolling(s).min()) / 2).shift(b)
    top, bot = np.maximum(spa, spb), np.minimum(spa, spb)
    return pd.Series(np.where((c > top) & (ten > kij), 1.0, np.where((c < bot) & (ten < kij), -1.0, 0.0)), index=c.index)


def heikin_ashi(df, k):
    hac = (df.open + df.high + df.low + df.close) / 4
    hao = hac.copy(); hao.iloc[0] = (df.open.iloc[0] + df.close.iloc[0]) / 2
    o, cc = np.array(hao.to_numpy(), dtype=float), np.array(hac.to_numpy(), dtype=float)
    for t in range(1, len(o)):
        o[t] = (o[t - 1] + cc[t - 1]) / 2
    green = pd.Series(cc > o, index=df.index)
    up = green.rolling(k).sum() == k; dn = (~green).rolling(k).sum() == k
    return pd.Series(_state(up, dn, dn, up), index=df.index)


def apply_mode(s, mode):
    return s.clip(lower=0) if mode == "LO" else s
