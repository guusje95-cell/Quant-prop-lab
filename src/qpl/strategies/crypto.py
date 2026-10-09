"""Crypto signal library (V4). Each function maps bars (+ optional extras) to a TARGET POSITION
series w[t] using only data up to the close of bar t. Positions are fractions of equity."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtesting.vector import vol_target


def hold_for(sig: pd.Series, h: int) -> pd.Series:
    """Keep each non-zero signal for h bars (h >= 1)."""
    x = sig.replace(0, np.nan)
    return (x.ffill(limit=h - 1) if h > 1 else x).fillna(0.0)


def _bpy(bars):
    step = (bars.index[1] - bars.index[0]).total_seconds()
    return 365 * 86400 / step


def buy_hold_vt(bars, p):
    return vol_target(pd.Series(1.0, index=bars.index), bars, p.get("target_vol", 0.4), p.get("vol_lb", 30), _bpy(bars))


def tsmom(bars, p):
    """C1: sign of trailing L-bar return; long/short or long/flat; vol-targeted."""
    L = p["lookback"]
    s = np.sign(np.log(bars["close"]).diff(L))
    if p.get("long_only"):
        s = s.clip(lower=0)
    return vol_target(s, bars, p.get("target_vol", 0.4), p.get("vol_lb", 30), _bpy(bars))


def donchian(bars, p):
    """C2: enter on close above N-bar high (below N-bar low), exit on close through the N/2 channel."""
    N, X = p["n"], max(2, p["n"] // 2)
    c = bars["close"]
    hi, lo = bars["high"].rolling(N).max().shift(1), bars["low"].rolling(N).min().shift(1)
    xhi, xlo = bars["high"].rolling(X).max().shift(1), bars["low"].rolling(X).min().shift(1)
    pos = np.zeros(len(c)); cur = 0
    cv, h_, l_, xh, xl = c.to_numpy(), hi.to_numpy(), lo.to_numpy(), xhi.to_numpy(), xlo.to_numpy()
    for t in range(len(c)):
        if cur == 0:
            if cv[t] > h_[t]:
                cur = 1
            elif cv[t] < l_[t] and not p.get("long_only"):
                cur = -1
        elif cur == 1 and cv[t] < xl[t]:
            cur = 0
        elif cur == -1 and cv[t] > xh[t]:
            cur = 0
        pos[t] = cur
    return vol_target(pd.Series(pos, index=c.index), bars, p.get("target_vol", 0.4), p.get("vol_lb", 30), _bpy(bars))


def reversal(bars, p):
    """C3: after a bar return beyond k trailing sigmas, take the opposite side for h bars."""
    k, h, lb = p["k"], p["hold"], p.get("lb", 168)
    r = np.log(bars["close"]).diff()
    z = r / r.rolling(lb, min_periods=lb // 2).std().shift(1)
    trig = (-np.sign(z)).where(z.abs() > k, 0.0)
    pos = hold_for(trig, h)
    if p.get("long_only"):
        pos = pos.clip(lower=0)
    return pos * p.get("size", 1.0)


def vol_expansion(bars, p):
    """C4: after a range-expansion bar (range > x * ATR) closing in its top/bottom quartile, follow it for h bars."""
    x, h = p["x"], p["hold"]
    rng = bars["high"] - bars["low"]
    atr = rng.rolling(20).mean().shift(1)
    loc = (bars["close"] - bars["low"]) / rng.replace(0, np.nan)
    sig = pd.Series(0.0, index=bars.index)
    sig[(rng > x * atr) & (loc > 0.75)] = 1.0
    sig[(rng > x * atr) & (loc < 0.25)] = -1.0
    pos = hold_for(sig, h)
    if p.get("long_only"):
        pos = pos.clip(lower=0)
    return vol_target(pos, bars, p.get("target_vol", 0.4), p.get("vol_lb", 30), _bpy(bars))


def funding_contrarian(bars, p, funding: pd.Series):
    """C6: when the latest funding print is in the top (bottom) q of its trailing distribution
    (crowded longs/shorts), take the contrarian side for `hold` bars."""
    q, hold, lb = p["q"], p["hold"], p.get("lb_settlements", 270)
    f = funding.sort_index()
    hi = f.rolling(lb, min_periods=lb // 2).quantile(q).shift(1)
    lo = f.rolling(lb, min_periods=lb // 2).quantile(1 - q).shift(1)
    sig = pd.Series(np.where(f > hi, -1.0, np.where(f < lo, 1.0, 0.0)), index=f.index)
    # a settlement at time s is known after s: map to the first bar whose CLOSE is >= s
    step = bars.index[1] - bars.index[0]
    bar_of = bars.index.searchsorted(sig.index - step, side="left")
    w = pd.Series(0.0, index=bars.index)
    ok = bar_of < len(bars)
    w.iloc[bar_of[ok]] = sig.to_numpy()[ok]
    w = hold_for(w, hold)
    if p.get("long_only"):
        w = w.clip(lower=0)
    return w * p.get("size", 1.0)


SIGNALS = {"buy_hold_vt": buy_hold_vt, "tsmom": tsmom, "donchian": donchian, "reversal": reversal,
           "vol_expansion": vol_expansion}


def trend_ensemble(bars, p):
    """Frozen V4 candidate CT1: equal-weight mean of TSMOM(20,60,120) and Donchian(20,55),
    each vol-targeted; long/short unless long_only."""
    tv, lo = p.get("target_vol", 0.4), p.get("long_only", False)
    parts = [tsmom(bars, {"lookback": L, "target_vol": tv, "long_only": lo}) for L in p.get("tsmom", (20, 60, 120))]
    parts += [donchian(bars, {"n": n, "target_vol": tv, "long_only": lo}) for n in p.get("donchian", (20, 55))]
    return pd.concat(parts, axis=1).fillna(0).mean(axis=1)


SIGNALS["trend_ensemble"] = trend_ensemble
