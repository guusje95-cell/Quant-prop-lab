"""Generation-1 intraday hypotheses for US equity-index futures (Topstep compatible:
every position is closed before 16:00 ET, or - for overnight-session hypotheses -
inside one CME trading day, i.e. before the 16:10 ET Topstep cut-off).

All functions: (ctx, params) -> Orders. ctx is a prepared frame (features.intraday.prepare
+ add_prev_close) with extra arrays cached in ctx.attrs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtesting.engine import MARKET, STOP, Orders
from ..features.intraday import add_prev_close, asof_prior, atr_series, daily_rth_table, day_ordinal, prepare


def build_context(df: pd.DataFrame, bar_min: int) -> pd.DataFrame:
    p = prepare(df, bar_min)
    p = add_prev_close(p, bar_min)
    t = daily_rth_table(p)
    dates = p["date"].to_numpy()
    p["atr_d"] = asof_prior(atr_series(t, 14), dates)     # ATR through the prior day (known pre-open)
    # daily close-to-close vol (points) through the prior day: sizing reference
    p["sd_d"] = asof_prior(t["close"].diff().rolling(20, min_periods=15).std(), dates)
    p.attrs["bar_min"] = bar_min
    # last RTH bar actually present in each valid day -> forced flat bar
    rth_ok = p["rth"].to_numpy() & p["valid_day"].to_numpy()
    last = np.zeros(len(p), bool)
    if rth_ok.any():
        pos = np.flatnonzero(rth_ok)
        d = p["date"].to_numpy()[pos]
        is_last = np.r_[d[1:] != d[:-1], True]
        last[pos[is_last]] = True
    p["flat_rth"] = last
    return p


def rth_session(ctx) -> np.ndarray:
    return ctx["sess"].to_numpy()


def cme_session(ctx) -> np.ndarray:
    return day_ordinal(ctx["cme_date"].to_numpy())


# --------------------------------------------------------------------------------------
# H1: Opening-range breakout
# --------------------------------------------------------------------------------------
def orb(ctx: pd.DataFrame, prm: dict) -> Orders:
    """Opening range = first `or_bars` RTH bars. Modes:
       candle_mkt : enter at next open in the direction of the OR candle (close vs open)
       bracket    : OCO stop orders at OR high / OR low, valid until `last_entry_min`
    Stop: 'or' = opposite OR extreme, or float f = f * OR range from entry.
    Target: tgt_R multiple of initial risk (nan = hold to the close)."""
    n = len(ctx)
    o = Orders(n)
    k = prm.get("or_bars", 2)
    mode = prm.get("mode", "candle_mkt")
    stop = prm.get("stop", "or")
    tgt_R = prm.get("tgt_R", np.nan)
    last_entry = prm.get("last_entry_min", 12 * 60)
    min_rng_atr = prm.get("min_range_atr", 0.0)
    bar_min = ctx.attrs["bar_min"]
    rb = ctx["rth_bar"].to_numpy()
    valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    H, L, O, C = (ctx[c].to_numpy() for c in ("high", "low", "open", "close"))
    atr = ctx["atr_d"].to_numpy()
    date = ctx["date"].to_numpy()
    et = ctx["et_min"].to_numpy()
    sig = np.flatnonzero((rb == k - 1) & valid)
    for t in sig:
        s = t - (k - 1)
        if s < 0 or date[s] != date[t] or rb[s] != 0:
            continue
        orh, orl = H[s:t + 1].max(), L[s:t + 1].min()
        rng = orh - orl
        if rng <= 0 or not np.isfinite(atr[t]) or rng < min_rng_atr * atr[t]:
            continue
        expiry = t + max(1, (last_entry - (et[t] + bar_min)) // bar_min + 1)
        if mode == "candle_mkt":
            d = 1 if C[t] > O[s] else (-1 if C[t] < O[s] else 0)
            if d == 0:
                continue
            o.entry_dir[t] = d
            o.entry_type[t] = MARKET
            if stop == "or":
                o.stop_px[t] = orl if d > 0 else orh
                risk = abs(C[t] - o.stop_px[t])
            else:
                o.stop_dist[t] = float(stop) * rng
                risk = float(stop) * rng
            if np.isfinite(tgt_R):
                o.tgt_dist[t] = tgt_R * risk
        elif mode == "bracket":
            o.entry_dir[t] = 2
            o.entry_type[t] = STOP
            o.entry_px[t] = orh
            o.entry_px2[t] = orl
            o.entry_expiry[t] = expiry
            if stop != "or":
                o.stop_dist[t] = float(stop) * rng
            if np.isfinite(tgt_R):
                o.tgt_dist[t] = tgt_R * (float(stop) * rng if stop != "or" else rng)
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = 1
    return o


# --------------------------------------------------------------------------------------
# H2: Intraday momentum (Gao, Han, Li & Zhou 2018): first half-hour return (incl. overnight)
# predicts the last half-hour return.
# --------------------------------------------------------------------------------------
def intraday_momentum(ctx: pd.DataFrame, prm: dict) -> Orders:
    n = len(ctx)
    o = Orders(n)
    bar_min = ctx.attrs["bar_min"]
    entry_min = prm.get("entry_min", 15 * 60 + 30)       # last half hour starts 15:30
    sig_end = prm.get("signal_end_min", 10 * 60)          # first half hour ends 10:00
    use_r12 = prm.get("use_r12", False)
    thr = prm.get("thr_sd", 0.0)                          # |r1| threshold in daily-sd units
    et = ctx["et_min"].to_numpy()
    C = ctx["close"].to_numpy()
    date = ctx["date"].to_numpy()
    pc = ctx["prev_rth_close"].to_numpy()
    sd = ctx["sd_d"].to_numpy()
    valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    # close at 10:00 (bar ending at sig_end) per date
    end10 = pd.Series(C[et + bar_min == sig_end], index=date[et + bar_min == sig_end])
    end10 = end10[~end10.index.duplicated()]
    c10 = pd.Series(date).map(end10).to_numpy()
    # close at 15:00 for r12 (15:00-15:30)
    m15 = et + bar_min == entry_min - 30
    c1500 = pd.Series(C[m15], index=date[m15])
    c1500 = c1500[~c1500.index.duplicated()]
    c15 = pd.Series(date).map(c1500).to_numpy()
    sigbar = np.flatnonzero((et + bar_min == entry_min) & valid)
    for t in sigbar:
        if not (np.isfinite(pc[t]) and np.isfinite(c10[t]) and np.isfinite(sd[t])):
            continue
        r1 = c10[t] - pc[t]
        if abs(r1) < thr * sd[t]:
            continue
        s = np.sign(r1)
        if use_r12 and np.isfinite(c15[t]):
            r12 = C[t] - c15[t]
            if np.sign(r12) != s:
                continue
        o.entry_dir[t] = int(s)
        o.entry_type[t] = MARKET
        o.risk_ref[t] = 0.25 * sd[t]
        if np.isfinite(prm.get("stop_sd", np.nan)):
            o.stop_dist[t] = prm["stop_sd"] * sd[t]
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = 1
    return o


# --------------------------------------------------------------------------------------
# H3: Noise-area intraday momentum (Zarattini, Aziz & Barbon 2024)
# --------------------------------------------------------------------------------------
def noise_area(ctx: pd.DataFrame, prm: dict) -> Orders:
    n = len(ctx)
    o = Orders(n)
    bar_min = ctx.attrs["bar_min"]
    lb = prm.get("lookback", 14)
    mult = prm.get("mult", 1.0)
    check = prm.get("check_min", 30)
    first_check = prm.get("first_check_min", 10 * 60)
    trail = prm.get("trail", "band_mean")      # 'band' or 'band_mean'
    last_entry = prm.get("last_entry_min", 15 * 60 + 30)
    rb = ctx["rth_bar"].to_numpy()
    rth = ctx["rth"].to_numpy() & ctx["valid_day"].to_numpy()
    C, H, L = ctx["close"].to_numpy(), ctx["high"].to_numpy(), ctx["low"].to_numpy()
    op = ctx["rth_open"].to_numpy()
    pc = ctx["prev_rth_close"].to_numpy()
    et = ctx["et_min"].to_numpy()
    date = ctx["date"].to_numpy()
    sd = ctx["sd_d"].to_numpy()
    # sigma by time-of-day slot over previous `lb` days (strictly prior days)
    mv = pd.DataFrame({"date": date[rth], "slot": rb[rth], "mv": np.abs(C[rth] / op[rth] - 1)})
    piv = mv.pivot_table(index="date", columns="slot", values="mv", aggfunc="last")
    sig = piv.rolling(lb, min_periods=lb).mean().shift(1)
    sig_long = sig.stack()
    key = pd.MultiIndex.from_arrays([date, rb])
    s_arr = sig_long.reindex(key).to_numpy()
    # running mean of typical price since the open (TWAP proxy for VWAP: CFD volume is not usable)
    tp = (H + L + C) / 3.0
    df = pd.DataFrame({"d": date, "tp": np.where(rth, tp, np.nan)})
    twap = df.groupby("d")["tp"].transform(lambda x: x.expanding().mean()).to_numpy()
    ub = np.maximum(op, pc) * (1 + mult * s_arr)
    lbd = np.minimum(op, pc) * (1 - mult * s_arr)
    is_check = rth & ((et + bar_min) % check == 0) & (et + bar_min >= first_check)
    ok = is_check & np.isfinite(ub) & np.isfinite(lbd) & np.isfinite(sd)
    if trail == "band_mean":
        long_stop = np.maximum(ub, twap)
        short_stop = np.minimum(lbd, twap)
    else:
        long_stop, short_stop = ub, lbd
    can_enter = ok & (et + bar_min <= last_entry)
    o.entry_dir[can_enter & (C > ub)] = 1
    o.entry_dir[can_enter & (C < lbd)] = -1
    o.entry_type[o.entry_dir != 0] = MARKET
    o.risk_ref[:] = sd
    ex_long = ok & (C < long_stop)
    ex_short = ok & (C > short_stop)
    o.exit_sig[ex_long] = 1
    o.exit_sig[ex_short & ~ex_long] = -1
    o.exit_sig[ex_short & ex_long] = 2
    cat = prm.get("cat_stop_sd", 1.5)
    o.stop_dist[:] = cat * sd
    o.flat_bar = ctx["flat_rth"].to_numpy().copy()
    o.max_trades_sess = prm.get("max_trades", 6)
    return o


# --------------------------------------------------------------------------------------
# H4: Overnight drift (Boyarchenko, Larsen & Whelan 2023): ES returns accrue overnight,
# concentrated around the European open. Long from Globex reopen to a morning exit.
# --------------------------------------------------------------------------------------
def overnight_drift(ctx: pd.DataFrame, prm: dict) -> Orders:
    n = len(ctx)
    o = Orders(n)
    bar_min = ctx.attrs["bar_min"]
    entry_min = prm.get("entry_min", 18 * 60)
    exit_min = prm.get("exit_min", 9 * 60 + 30)
    stop_atr = prm.get("stop_atr", np.nan)
    dows = prm.get("dows", (0, 1, 2, 3, 4))   # weekday of the CME trading date
    side = prm.get("side", 1)
    et = ctx["et_min"].to_numpy()
    cd = pd.DatetimeIndex(ctx["cme_date"])
    from ..data.calendar import holidays
    bad = cd.isin(holidays()) | (cd.dayofweek >= 5)
    cd_dow = cd.dayofweek.to_numpy()
    atr = ctx["atr_d"].to_numpy()
    sd = ctx["sd_d"].to_numpy()
    sess = cme_session(ctx)
    # entry: signal on bar t when bar t+1 is the first bar at/after entry_min within its CME session
    nxt_et = np.r_[et[1:], -1]
    nxt_sess = np.r_[sess[1:], -1]
    nxt_bad = np.r_[bad[1:], True]
    nxt_dow = np.r_[cd_dow[1:], -1]
    # first bar of a session at/after entry_min: entry_min in [18:00, 24:00) or early morning
    def at_or_after(m):
        if entry_min >= 18 * 60:
            return (m >= entry_min) | (m < 17 * 60)
        return (m >= entry_min) & (m < 17 * 60)
    cur_ok = ~at_or_after(et) | (sess != nxt_sess)
    trig = at_or_after(nxt_et) & cur_ok & ~nxt_bad & np.isin(nxt_dow, dows)
    # exit bar: bar whose close == exit_min (same CME session)
    o.flat_bar = (et < exit_min) & (et + bar_min >= exit_min)
    # never hold through the 16:00-16:10 ET cut-off: also flat on the last RTH bar
    o.flat_bar |= ctx["flat_rth"].to_numpy()
    t_idx = np.flatnonzero(trig)
    for t in t_idx:
        a = atr[t + 1] if t + 1 < n else np.nan
        if not np.isfinite(a):
            continue
        o.entry_dir[t] = side
        o.entry_type[t] = MARKET
        o.risk_ref[t] = 0.5 * a
        if np.isfinite(stop_atr):
            o.stop_dist[t] = stop_atr * a
    # the signal bar belongs to the previous CME session; one trigger per session already
    o.max_trades_sess = 100
    return o


# --------------------------------------------------------------------------------------
# H5: Opening-gap fade toward the prior RTH close
# --------------------------------------------------------------------------------------
def gap_fade(ctx: pd.DataFrame, prm: dict) -> Orders:
    n = len(ctx)
    o = Orders(n)
    bar_min = ctx.attrs["bar_min"]
    gmin, gmax = prm.get("gap_min_atr", 0.3), prm.get("gap_max_atr", 1.5)
    stop_atr = prm.get("stop_atr", 0.5)
    exit_min = prm.get("exit_min", 12 * 60)
    rb = ctx["rth_bar"].to_numpy()
    valid = ctx["valid_day"].to_numpy() & ctx["rth"].to_numpy()
    C = ctx["close"].to_numpy()
    op = ctx["rth_open"].to_numpy()
    pc = ctx["prev_rth_close"].to_numpy()
    atr = ctx["atr_d"].to_numpy()
    et = ctx["et_min"].to_numpy()
    t_idx = np.flatnonzero((rb == 0) & valid)
    for t in t_idx:
        if not (np.isfinite(pc[t]) and np.isfinite(atr[t]) and np.isfinite(op[t])):
            continue
        g = (op[t] - pc[t]) / atr[t]
        if not (gmin <= abs(g) <= gmax):
            continue
        d = -int(np.sign(g))
        dist = (pc[t] - C[t]) * d
        if dist <= 0:
            continue    # gap already filled in the first bar
        o.entry_dir[t] = d
        o.entry_type[t] = MARKET
        o.stop_dist[t] = stop_atr * atr[t]
        o.tgt_dist[t] = dist
    o.flat_bar = (et < exit_min) & (et + bar_min >= exit_min) & ctx["rth"].to_numpy()
    o.flat_bar |= ctx["flat_rth"].to_numpy()
    o.max_trades_sess = 1
    return o


STRATEGIES = {
    "orb": orb, "intraday_momentum": intraday_momentum, "noise_area": noise_area,
    "overnight_drift": overnight_drift, "gap_fade": gap_fade,
}
SESSION_KIND = {"overnight_drift": "cme"}
