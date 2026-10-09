"""v3 hypotheses (generation 7). Same Orders interface as index_intraday; all features causal.
Registered into index_intraday.STRATEGIES on import."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtesting.engine import LIMIT, MARKET, STOP, Orders
from ..features.intraday import asof_prior, daily_rth_table
from . import index_intraday as SI


def _tod_sigma(ctx, lb=20):
    """Time-of-day sigma of single-bar log returns over the previous `lb` sessions (today excluded)."""
    rth = ctx["rth"].to_numpy() & ctx["valid_day"].to_numpy()
    C = ctx["close"].to_numpy()
    O = ctx["open"].to_numpy()
    r = np.log(C / O)
    date = ctx["date"].to_numpy(); rb = ctx["rth_bar"].to_numpy()
    df = pd.DataFrame({"date": date[rth], "slot": rb[rth], "r": np.abs(r[rth])})
    piv = df.pivot_table(index="date", columns="slot", values="r", aggfunc="last")
    s = piv.rolling(lb, min_periods=lb).mean().shift(1).stack()
    return s.reindex(pd.MultiIndex.from_arrays([date, rb])).to_numpy(), r


def _twap(ctx):
    rth = ctx["rth"].to_numpy() & ctx["valid_day"].to_numpy()
    tp = (ctx["high"].to_numpy() + ctx["low"].to_numpy() + ctx["close"].to_numpy()) / 3
    return pd.DataFrame({"d": ctx["date"].to_numpy(), "tp": np.where(rth, tp, np.nan)}).groupby("d")["tp"].transform(
        lambda x: x.expanding().mean()).to_numpy()


def _prior_day(ctx):
    t = daily_rth_table(ctx)
    d = ctx["date"].to_numpy()
    return {k: asof_prior(t[k], d) for k in ("high", "low", "close", "open")} | {
        "range_ratio": asof_prior((t["high"] - t["low"]) / (t["high"] - t["low"]).rolling(20, min_periods=15).mean(), d)}


# V1: failed breakout of the prior-day high/low -> revert toward session mean
def failed_breakout(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    back_bars = prm.get("back_bars", 2); stop_buf = prm.get("stop_buf_atr", 0.1)
    rth = ctx["rth"].to_numpy() & ctx["valid_day"].to_numpy()
    H, L, C = ctx["high"].to_numpy(), ctx["low"].to_numpy(), ctx["close"].to_numpy()
    date = ctx["date"].to_numpy(); et = ctx["et_min"].to_numpy(); atr = ctx["atr_d"].to_numpy()
    pdv = _prior_day(ctx); pdh, pdl = pdv["high"], pdv["low"]
    tw = _twap(ctx)
    last_breach_up = -10**9; last_breach_dn = -10**9; cur = None; sess_hi = -np.inf; sess_lo = np.inf
    for t in range(n):
        if not rth[t]:
            continue
        if date[t] != cur:
            cur = date[t]; last_breach_up = last_breach_dn = -10**9; sess_hi, sess_lo = -np.inf, np.inf
        sess_hi = max(sess_hi, H[t]); sess_lo = min(sess_lo, L[t])
        if not (np.isfinite(pdh[t]) and np.isfinite(atr[t])) or et[t] + bm > 15 * 60:
            continue
        if H[t] > pdh[t]:
            last_breach_up = t
        if L[t] < pdl[t]:
            last_breach_dn = t
        # failed upside breakout: traded above PDH recently, now closes back below it
        if 0 <= t - last_breach_up <= back_bars and C[t] < pdh[t] and np.isfinite(tw[t]) and tw[t] < C[t]:
            o.entry_dir[t] = -1; o.entry_type[t] = MARKET
            o.stop_px[t] = sess_hi + stop_buf * atr[t]; o.tgt_dist[t] = C[t] - tw[t]
        elif 0 <= t - last_breach_dn <= back_bars and C[t] > pdl[t] and np.isfinite(tw[t]) and tw[t] > C[t]:
            o.entry_dir[t] = 1; o.entry_type[t] = MARKET
            o.stop_px[t] = sess_lo - stop_buf * atr[t]; o.tgt_dist[t] = tw[t] - C[t]
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = prm.get("max_trades", 2)
    return o


# V2: reversion after an extreme single-bar move (time-of-day normalized)
def extreme_reversion(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    k = prm.get("k", 3.0); hold = prm.get("hold_bars", 4)
    sig, r = _tod_sigma(ctx, prm.get("lookback", 20))
    rth = ctx["rth"].to_numpy() & ctx["valid_day"].to_numpy()
    et = ctx["et_min"].to_numpy(); rb = ctx["rth_bar"].to_numpy()
    H, L, C = ctx["high"].to_numpy(), ctx["low"].to_numpy(), ctx["close"].to_numpy()
    z = r / sig
    ok = rth & np.isfinite(z) & (rb >= 1) & (et + bm <= 15 * 60)
    for t in np.flatnonzero(ok & (np.abs(z) > k)):
        d = -int(np.sign(z[t]))
        o.entry_dir[t] = d; o.entry_type[t] = MARKET
        o.stop_px[t] = H[t] + 0.25 * (H[t] - L[t]) if d < 0 else L[t] - 0.25 * (H[t] - L[t])
        # time exit after `hold` bars: exit signal on bar t+hold (both directions)
        if t + hold < n:
            o.exit_sig[t + hold] = 2
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = prm.get("max_trades", 3)
    return o


# V3: opening-range breakout only after volatility compression (prior day range << 20d average)
def compression_breakout(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    k = prm.get("or_bars", 2); thr = prm.get("range_ratio_max", 0.7); tgt_R = prm.get("tgt_R", np.nan)
    invert = prm.get("invert", False)   # baseline: same breakout on NON-compressed days
    rb = ctx["rth_bar"].to_numpy(); valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    H, L = ctx["high"].to_numpy(), ctx["low"].to_numpy(); date = ctx["date"].to_numpy(); et = ctx["et_min"].to_numpy()
    rr = _prior_day(ctx)["range_ratio"]
    for t in np.flatnonzero((rb == k - 1) & valid):
        s = t - (k - 1)
        if s < 0 or date[s] != date[t] or rb[s] != 0 or not np.isfinite(rr[t]):
            continue
        cond = rr[t] <= thr
        if (not invert and not cond) or (invert and cond):
            continue
        orh, orl = H[s:t + 1].max(), L[s:t + 1].min()
        if orh <= orl:
            continue
        o.entry_dir[t] = 2; o.entry_type[t] = STOP; o.entry_px[t] = orh; o.entry_px2[t] = orl
        o.entry_expiry[t] = t + max(1, (12 * 60 - (et[t] + bm)) // bm + 1)
        if np.isfinite(tgt_R):
            o.tgt_dist[t] = tgt_R * (orh - orl)
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = 1
    return o


# V4: turn-of-month: long during RTH (or the preceding overnight session) on TOM days
def turn_of_month(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    window = prm.get("window", (-1, 3))      # trading-day offsets: last day of month .. 3rd day
    invert = prm.get("invert", False)        # baseline: non-TOM days
    rb = ctx["rth_bar"].to_numpy(); valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    from ..data.calendar import holidays
    d0, d1 = pd.Timestamp(ctx["date"].min()), pd.Timestamp(ctx["date"].max()) + pd.offsets.MonthEnd(1)
    bd = pd.bdate_range(d0 - pd.offsets.MonthBegin(1), d1)
    days = bd[~bd.isin(holidays())]
    # trading-day index within month from the EXCHANGE CALENDAR (ex-ante), never from data availability
    ym = days.year * 100 + days.month
    first = pd.Series(np.arange(len(days)), index=days).groupby(ym).transform("min").to_numpy()
    last = pd.Series(np.arange(len(days)), index=days).groupby(ym).transform("max").to_numpy()
    pos = np.arange(len(days)) - first + 1          # 1 = first trading day
    tom = set(days[(pos <= window[1]) | (np.arange(len(days)) == last)])
    date = ctx["date"].to_numpy()
    for t in np.flatnonzero((rb == 0) & valid):
        is_tom = pd.Timestamp(date[t]) in tom
        if is_tom == invert:
            continue
        if t > 0:
            o.entry_dir[t - 1] = 1; o.entry_type[t - 1] = MARKET      # enter at the 09:30 open
            o.risk_ref[t - 1] = ctx["sd_d"].to_numpy()[t]
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = 1
    return o


# V10: H3 entry improvement - after a noise-area breakout signal, buy a pullback to the session TWAP
def noise_pullback(ctx, prm):
    base = SI.noise_area(ctx, prm)
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    tw = _twap(ctx); C = ctx["close"].to_numpy(); date = ctx["date"].to_numpy()
    wait = prm.get("wait_bars", 8)
    for t in np.flatnonzero(base.entry_dir != 0):
        d = base.entry_dir[t]
        if not np.isfinite(tw[t]):
            continue
        lim = tw[t] if (d > 0 and tw[t] < C[t]) or (d < 0 and tw[t] > C[t]) else C[t]
        o.entry_dir[t] = d; o.entry_type[t] = LIMIT; o.entry_px[t] = lim; o.entry_expiry[t] = t + wait
        o.stop_dist[t] = base.stop_dist[t]; o.risk_ref[t] = base.risk_ref[t]
    o.exit_sig = base.exit_sig.copy(); o.flat_bar = base.flat_bar.copy(); o.max_trades_sess = base.max_trades_sess
    return o


# V9 (exploratory, sign-reversal of rejected H5): gap continuation
def gap_continuation(ctx, prm):
    n = len(ctx); o = Orders(n)
    gmin, gmax = prm.get("gap_min_atr", 0.3), prm.get("gap_max_atr", 1.5)
    rb = ctx["rth_bar"].to_numpy(); valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    op, pc, atr = ctx["rth_open"].to_numpy(), ctx["prev_rth_close"].to_numpy(), ctx["atr_d"].to_numpy()
    for t in np.flatnonzero((rb == 0) & valid):
        if not (np.isfinite(pc[t]) and np.isfinite(atr[t]) and np.isfinite(op[t])):
            continue
        g = (op[t] - pc[t]) / atr[t]
        if gmin <= abs(g) <= gmax:
            o.entry_dir[t] = int(np.sign(g)); o.entry_type[t] = MARKET; o.stop_dist[t] = prm.get("stop_atr", 0.5) * atr[t]
    o.flat_bar = ctx["flat_rth"].to_numpy().copy(); o.max_trades_sess = 1
    return o


SI.STRATEGIES.update({"failed_breakout": failed_breakout, "extreme_reversion": extreme_reversion,
                      "compression_breakout": compression_breakout, "turn_of_month": turn_of_month,
                      "noise_pullback": noise_pullback, "gap_continuation": gap_continuation})


# V11: Asian-range breakout at the London open (FX / gold); CME-session based (18:00 ET start)
def asian_breakout(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    a0, a1 = prm.get("asia_start", 19 * 60), prm.get("asia_end", 3 * 60)
    x_min = prm.get("exit_min", 11 * 60); stop_frac = prm.get("stop_frac", np.nan)
    et = ctx["et_min"].to_numpy(); H, L = ctx["high"].to_numpy(), ctx["low"].to_numpy()
    sess = SI.cme_session(ctx)
    in_asia = (et >= a0) | (et < a1)
    hi = lo = None; cur = None
    from ..data.calendar import holidays
    cd = pd.DatetimeIndex(ctx["cme_date"]); bad = cd.isin(holidays()) | (cd.dayofweek >= 5)
    for t in range(n):
        if sess[t] != cur:
            cur = sess[t]; hi, lo = -np.inf, np.inf
        if in_asia[t] and not (et[t] >= 17 * 60 and et[t] < a0):
            hi = max(hi, H[t]); lo = min(lo, L[t])
        # signal on the last Asian bar (bar ending at a1)
        if et[t] + bm == a1 and np.isfinite(hi) and hi > lo and not bad[t]:
            o.entry_dir[t] = 2; o.entry_type[t] = STOP; o.entry_px[t] = hi; o.entry_px2[t] = lo
            o.entry_expiry[t] = t + max(1, (x_min - 60 - a1) // bm)
            if np.isfinite(stop_frac):
                o.stop_dist[t] = stop_frac * (hi - lo)
    o.flat_bar = (et < x_min) & (et + bm >= x_min)
    o.max_trades_sess = 1
    return o


# V12: Asian-session mean reversion toward the session open (FX)
def asian_reversion(ctx, prm):
    n = len(ctx); o = Orders(n); bm = ctx.attrs["bar_min"]
    k = prm.get("k", 1.5); s0, s1, x_min = prm.get("start", 19 * 60), prm.get("last_entry", 23 * 60), prm.get("exit_min", 2 * 60)
    et = ctx["et_min"].to_numpy(); C, O = ctx["close"].to_numpy(), ctx["open"].to_numpy()
    sess = SI.cme_session(ctx); atr = ctx["atr_d"].to_numpy()
    ref = np.full(n, np.nan); cur = None; r0 = np.nan
    for t in range(n):
        if sess[t] != cur:
            cur = sess[t]; r0 = np.nan
        if et[t] == s0:
            r0 = O[t]
        ref[t] = r0
    dev = (C - ref) / (atr * 0.25)
    win = (et >= s0) & (et + bm <= s1) & np.isfinite(dev)
    for t in np.flatnonzero(win & (np.abs(dev) > k)):
        d = -int(np.sign(dev[t]))
        o.entry_dir[t] = d; o.entry_type[t] = MARKET
        o.tgt_dist[t] = abs(C[t] - ref[t]); o.stop_dist[t] = abs(C[t] - ref[t])
    o.flat_bar = (et < x_min) & (et + bm >= x_min)
    o.max_trades_sess = 1
    return o


SI.STRATEGIES.update({"asian_breakout": asian_breakout, "asian_reversion": asian_reversion})
SI.SESSION_KIND.update({"asian_breakout": "cme", "asian_reversion": "cme"})
