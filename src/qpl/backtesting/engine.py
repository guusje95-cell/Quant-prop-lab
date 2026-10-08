"""Event-ordered bar backtester (single instrument, one position at a time).

Execution model (documented assumptions, all deliberately conservative):

* Signals are evaluated on the CLOSE of bar t (all of bar t's OHLC is known).
  Any resulting order can first execute during bar t+1. Same-bar execution of
  a signal is impossible by construction.
* MARKET orders fill at open[t+1] +/- slippage (slip_ticks * tick).
* STOP entry orders fill when the bar trades through the stop price, at
  max(stop, open) for buys / min(stop, open) for sells (gap-through fills
  are filled at the worse open price), plus slippage.
* LIMIT orders (entries and profit targets) only fill if price trades
  THROUGH the limit by at least one tick; no slippage, fill at limit (or the
  better open if the bar gaps through).
* Protective stops fill at the worse of the stop price and the bar open,
  plus slippage.
* If the protective stop and the target are both inside the same bar the
  STOP is assumed to have been hit first.
* For a stop-entry bar, the protective stop is checked against the whole bar
  range (the low may have printed before the entry - counted as a loss).
* Trailing stops are updated with the bar's extreme only AFTER the bar has
  finished, so they never benefit from intrabar ordering.
* exit_sig[t] (+1 exit longs / -1 exit shorts / 2 any) exits at open[t+1].
* flat_bar[t] forces an exit at close[t] (minus slippage) - used to model the
  prop-firm "flat by 3:10 PM CT" rule; pending entries are cancelled from the
  flat bar onwards and at every session change.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

NONE, MARKET, STOP, LIMIT = 0, 1, 2, 3

# exit reasons
EX_STOP, EX_TARGET, EX_SIGNAL, EX_FLAT, EX_END = 1, 2, 3, 4, 5


@njit(cache=True)
def _simulate(o, h, l, c, sess, entry_dir, entry_type, entry_px, entry_px2, entry_expiry,
              stop_px, stop_dist, tgt_dist, trail_dist, exit_sig, flat_bar,
              max_trades_sess, tick, slip_ticks):
    n = len(o)
    maxt = n // 2 + 2
    t_entry_i = np.empty(maxt, np.int64)
    t_exit_i = np.empty(maxt, np.int64)
    t_dir = np.empty(maxt, np.int64)
    t_entry_px = np.empty(maxt, np.float64)
    t_exit_px = np.empty(maxt, np.float64)
    t_stop0 = np.empty(maxt, np.float64)
    t_mae = np.empty(maxt, np.float64)
    t_mfe = np.empty(maxt, np.float64)
    t_reason = np.empty(maxt, np.int64)
    nt = 0
    slip = slip_ticks * tick

    pos = 0
    e_px = 0.0
    e_i = 0
    stop = np.nan
    tgt = np.nan
    trail = np.nan
    mae = 0.0
    mfe = 0.0
    stop0 = np.nan

    p_dir = 0
    p_type = NONE
    p_px = np.nan
    p_px2 = np.nan
    p_exp = -1
    p_stop_px = np.nan
    p_stop_d = np.nan
    p_tgt_d = np.nan
    p_trail_d = np.nan
    p_exit = False
    trades_in_sess = 0

    for t in range(n):
        if t > 0 and sess[t] != sess[t - 1]:
            trades_in_sess = 0
            if p_type != NONE and p_type != MARKET:
                p_type = NONE
                p_dir = 0
        exited_this_bar = False
        # --- (a) pending signal exit at open
        if p_exit and pos != 0:
            px = o[t] - slip * pos
            t_exit_i[nt] = t; t_exit_px[nt] = px; t_reason[nt] = EX_SIGNAL
            t_entry_i[nt] = e_i; t_dir[nt] = pos; t_entry_px[nt] = e_px
            t_mae[nt] = mae; t_mfe[nt] = mfe; t_stop0[nt] = stop0
            nt += 1
            pos = 0
            exited_this_bar = True
        p_exit = False
        # --- (b) pending entry
        entered_this_bar = False
        entry_kind = NONE
        if pos == 0 and p_type != NONE and not exited_this_bar:
            fill = np.nan
            if p_type == MARKET:
                fill = o[t] + slip * p_dir
            elif t <= p_exp:
                if p_type == STOP and p_dir == 2:
                    # OCO bracket: buy stop at p_px, sell stop at p_px2
                    up = h[t] >= p_px
                    dn = l[t] <= p_px2
                    side = 0
                    if up and dn:
                        if o[t] >= p_px:
                            side = 1
                        elif o[t] <= p_px2:
                            side = -1
                        elif (p_px - o[t]) <= (o[t] - p_px2):
                            side = 1
                        else:
                            side = -1
                    elif up:
                        side = 1
                    elif dn:
                        side = -1
                    if side == 1:
                        fill = max(p_px, o[t]) + slip
                    elif side == -1:
                        fill = min(p_px2, o[t]) - slip
                    if side != 0 and np.isnan(p_stop_px) and np.isnan(p_stop_d):
                        p_stop_px = p_px2 if side == 1 else p_px
                    if side != 0:
                        p_dir = side
                elif p_type == STOP:
                    if p_dir > 0 and h[t] >= p_px:
                        fill = max(p_px, o[t]) + slip
                    elif p_dir < 0 and l[t] <= p_px:
                        fill = min(p_px, o[t]) - slip
                elif p_type == LIMIT:
                    if p_dir > 0 and l[t] <= p_px - tick:
                        fill = min(p_px, o[t])
                    elif p_dir < 0 and h[t] >= p_px + tick:
                        fill = max(p_px, o[t])
            else:
                p_type = NONE
                p_dir = 0
            if not np.isnan(fill):
                pos = p_dir
                e_px = fill
                e_i = t
                entry_kind = p_type
                if not np.isnan(p_stop_px):
                    stop = p_stop_px
                elif not np.isnan(p_stop_d):
                    stop = fill - pos * p_stop_d
                else:
                    stop = np.nan
                stop0 = stop
                tgt = fill + pos * p_tgt_d if not np.isnan(p_tgt_d) else np.nan
                trail = p_trail_d
                mae = 0.0
                mfe = 0.0
                trades_in_sess += 1
                entered_this_bar = True
                p_type = NONE
                p_dir = 0
        # --- (c) manage open position within bar t
        if pos != 0:
            # excursions (conservative: whole bar counts, incl. entry bar)
            if pos > 0:
                mae = min(mae, l[t] - e_px)
                mfe = max(mfe, h[t] - e_px)
            else:
                mae = min(mae, e_px - h[t])
                mfe = max(mfe, e_px - l[t])
            hit_stop = False
            hit_tgt = False
            if not np.isnan(stop):
                if pos > 0 and l[t] <= stop:
                    hit_stop = True
                elif pos < 0 and h[t] >= stop:
                    hit_stop = True
            if not np.isnan(tgt) and not hit_stop:
                if pos > 0 and h[t] >= tgt + tick:
                    hit_tgt = True
                elif pos < 0 and l[t] <= tgt - tick:
                    hit_tgt = True
            if hit_stop:
                if entered_this_bar and entry_kind == MARKET:
                    ref = o[t]
                elif entered_this_bar:
                    ref = stop  # already inside the bar; stop fills at stop
                else:
                    ref = o[t]
                if pos > 0:
                    px = min(stop, ref) - slip
                else:
                    px = max(stop, ref) + slip
                t_exit_i[nt] = t; t_exit_px[nt] = px; t_reason[nt] = EX_STOP
                t_entry_i[nt] = e_i; t_dir[nt] = pos; t_entry_px[nt] = e_px
                t_mae[nt] = min(mae, (px - e_px) * pos); t_mfe[nt] = mfe; t_stop0[nt] = stop0
                nt += 1
                pos = 0
                exited_this_bar = True
            elif hit_tgt:
                if entered_this_bar:
                    px = tgt
                else:
                    px = max(tgt, o[t]) if pos > 0 else min(tgt, o[t])
                t_exit_i[nt] = t; t_exit_px[nt] = px; t_reason[nt] = EX_TARGET
                t_entry_i[nt] = e_i; t_dir[nt] = pos; t_entry_px[nt] = e_px
                t_mae[nt] = mae; t_mfe[nt] = mfe; t_stop0[nt] = stop0
                nt += 1
                pos = 0
                exited_this_bar = True
            elif flat_bar[t]:
                px = c[t] - slip * pos
                t_exit_i[nt] = t; t_exit_px[nt] = px; t_reason[nt] = EX_FLAT
                t_entry_i[nt] = e_i; t_dir[nt] = pos; t_entry_px[nt] = e_px
                t_mae[nt] = mae; t_mfe[nt] = mfe; t_stop0[nt] = stop0
                nt += 1
                pos = 0
                exited_this_bar = True
            else:
                # trailing stop update for NEXT bar (uses completed bar only)
                if not np.isnan(trail):
                    if pos > 0:
                        cand = h[t] - trail
                        if np.isnan(stop) or cand > stop:
                            stop = cand
                    else:
                        cand = l[t] + trail
                        if np.isnan(stop) or cand < stop:
                            stop = cand
        if flat_bar[t]:
            p_type = NONE
            p_dir = 0
            continue
        # --- (d) signals at close of bar t -> orders for bar t+1
        if pos != 0 and (exit_sig[t] == 2 or exit_sig[t] == pos):
            p_exit = True
        if pos == 0 and p_type == NONE and entry_dir[t] != 0 and trades_in_sess < max_trades_sess:
            p_dir = entry_dir[t]
            p_type = entry_type[t]
            p_px = entry_px[t]
            p_px2 = entry_px2[t]
            p_exp = entry_expiry[t]
            p_stop_px = stop_px[t]
            p_stop_d = stop_dist[t]
            p_tgt_d = tgt_dist[t]
            p_trail_d = trail_dist[t]
            if t + 1 < n and sess[t + 1] != sess[t] and p_type != MARKET:
                p_type = NONE
                p_dir = 0
    if pos != 0:
        t_exit_i[nt] = n - 1; t_exit_px[nt] = c[n - 1]; t_reason[nt] = EX_END
        t_entry_i[nt] = e_i; t_dir[nt] = pos; t_entry_px[nt] = e_px
        t_mae[nt] = mae; t_mfe[nt] = mfe; t_stop0[nt] = stop0
        nt += 1
    return (t_entry_i[:nt], t_exit_i[:nt], t_dir[:nt], t_entry_px[:nt], t_exit_px[:nt],
            t_stop0[:nt], t_mae[:nt], t_mfe[:nt], t_reason[:nt])


class Orders:
    """Container of per-bar order instructions produced by a strategy at bar close."""

    def __init__(self, n: int):
        self.entry_dir = np.zeros(n, np.int64)
        self.entry_type = np.zeros(n, np.int64)
        self.entry_px = np.full(n, np.nan)
        self.entry_px2 = np.full(n, np.nan)   # sell-stop level for OCO brackets (entry_dir == 2)
        self.risk_ref = np.full(n, np.nan)    # sizing reference (points) when no hard stop
        self.entry_expiry = np.full(n, n, np.int64)
        self.stop_px = np.full(n, np.nan)
        self.stop_dist = np.full(n, np.nan)
        self.tgt_dist = np.full(n, np.nan)
        self.trail_dist = np.full(n, np.nan)
        self.exit_sig = np.zeros(n, np.int64)   # 0 none, +1 exit longs, -1 exit shorts, 2 exit any
        self.flat_bar = np.zeros(n, np.bool_)
        self.max_trades_sess = 1_000_000


def run(df: pd.DataFrame, orders: Orders, sess: np.ndarray, tick: float, slip_ticks: float = 1.0) -> pd.DataFrame:
    """Run the simulator; return a trade list (prices in instrument points)."""
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    res = _simulate(o, h, l, c, np.asarray(sess, np.int64), orders.entry_dir, orders.entry_type,
                    orders.entry_px, orders.entry_px2, orders.entry_expiry, orders.stop_px, orders.stop_dist,
                    orders.tgt_dist, orders.trail_dist, orders.exit_sig, orders.flat_bar,
                    int(orders.max_trades_sess), float(tick), float(slip_ticks))
    ei, xi, d, epx, xpx, st0, mae, mfe, rsn = res
    idx = df.index
    tr = pd.DataFrame({
        "entry_ts": idx[ei], "exit_ts": idx[xi], "entry_i": ei, "exit_i": xi, "dir": d,
        "entry_px": epx, "exit_px": xpx, "stop0": st0, "mae_pts": mae, "mfe_pts": mfe, "reason": rsn,
    })
    tr["pnl_pts"] = (tr["exit_px"] - tr["entry_px"]) * tr["dir"]
    tr["risk_pts"] = np.where(np.isfinite(tr["stop0"]), (tr["entry_px"] - tr["stop0"]) * tr["dir"], np.nan)
    tr["sess"] = np.asarray(sess)[ei]
    # sizing reference: hard-stop distance if any, else the strategy's risk_ref at the signal bar
    sig_i = np.maximum(ei - 1, 0)
    rr = orders.risk_ref[sig_i]
    tr["risk_pts"] = np.where(np.isfinite(tr["risk_pts"]), tr["risk_pts"], rr)
    return tr
