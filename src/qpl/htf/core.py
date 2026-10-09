"""Track A: higher-timeframe (HTF) liquidity levels on 1-hour bars (protocol config/htf_protocol.json).

Causality contract
  * Day/week levels for a bar come only from COMPLETED previous trading days/weeks.
  * ATRd for a bar uses completed days only (rolling mean of true range, shifted one day).
  * An event is detected on bar i using bar i's OHLC (known at its close); entry is at open[i+1].
  * Stops are checked BEFORE targets inside a bar; a gap through the stop fills at the (worse) open.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

RISK_PER_TRADE = 0.0025      # ASSUMPTION used only to translate R into % returns for CAGR / vol / drawdown


def trading_keys(idx: pd.DatetimeIndex, kind: str) -> tuple[np.ndarray, np.ndarray]:
    if kind == "crypto":
        d = idx.tz_convert("UTC").normalize().tz_localize(None)
    else:                                   # futures / CFD / FX: day starts 17:00 New York
        d = (idx.tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    day = d.values.astype("datetime64[D]").astype(np.int64)
    iso = d.isocalendar()
    week = (iso["year"].to_numpy().astype(np.int64) * 100 + iso["week"].to_numpy().astype(np.int64))
    return day, week


def month_key(idx: pd.DatetimeIndex, kind: str) -> np.ndarray:
    d = idx.tz_convert("UTC") if kind == "crypto" else idx.tz_convert("America/New_York") + pd.Timedelta(hours=7)
    return (d.year * 100 + d.month).to_numpy().astype(np.int64)


def htf_frame(df: pd.DataFrame, kind: str, atr_days: int = 20) -> pd.DataFrame:
    """Per-bar levels: PDH/PDL, PWH/PWL, ATRd - all from completed periods only."""
    day, week = trading_keys(df.index, kind)
    x = pd.DataFrame({"high": df.high.to_numpy(), "low": df.low.to_numpy(), "close": df.close.to_numpy(), "day": day, "week": week})
    d = x.groupby("day").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    d["atr"] = tr.rolling(atr_days, min_periods=atr_days).mean().shift(1)     # completed days only
    d["pdh"], d["pdl"] = d.high.shift(1), d.low.shift(1)
    w = x.groupby("week").agg(high=("high", "max"), low=("low", "min"))
    w["pwh"], w["pwl"] = w.high.shift(1), w.low.shift(1)
    mo = month_key(df.index, kind)
    x["month"] = mo
    m = x.groupby("month").agg(high=("high", "max"), low=("low", "min"))
    m["pmh"], m["pml"] = m.high.shift(1), m.low.shift(1)
    out = pd.DataFrame(index=df.index)
    out["day"], out["week"], out["month"] = day, week, mo
    out["pmh"], out["pml"] = m["pmh"].reindex(mo).to_numpy(), m["pml"].reindex(mo).to_numpy()
    for c in ("atr", "pdh", "pdl"):
        out[c] = d[c].reindex(day).to_numpy()
    for c in ("pwh", "pwl"):
        out[c] = w[c].reindex(week).to_numpy()
    return out


@dataclass
class Event:
    i: int              # signal bar (closed)
    direction: int      # +1 long, -1 short
    stop: float
    strategy: str
    family: str
    level: float


def detect_events(df: pd.DataFrame, lv: pd.DataFrame, family: str, delta_k: float = 0.05, stop_k: float = 0.05,
                  bo_stop_k: float = 0.5, sr3_window: int = 3) -> list[Event]:
    """First-cross events per level and active period (no level re-use)."""
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    atr = lv.atr.to_numpy()
    col = {"PD": ("day", "pdh", "pdl"), "PW": ("week", "pwh", "pwl"), "PM": ("month", "pmh", "pml")}[family]
    key, hi_lv, lo_lv = (lv[c].to_numpy() for c in col)
    ev: list[Event] = []
    cur = None; used_hi = used_lo = False
    watch: list[tuple] = []           # pending SR3: (side, L, start_i, extreme)
    for i in range(len(c)):
        if key[i] != cur:
            cur = key[i]; used_hi = used_lo = False
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        dlt = delta_k * a
        # pending failed-breakout watches (from previous bars)
        nw = []
        for side, L, s, ext in watch:
            if side > 0:                                   # broke above high, waiting for close back below
                ext = max(ext, h[i])
                if c[i] < L:
                    ev.append(Event(i, -1, ext + stop_k * a, "A3_SR3", family, L)); continue
            else:
                ext = min(ext, l[i])
                if c[i] > L:
                    ev.append(Event(i, +1, ext - stop_k * a, "A3_SR3", family, L)); continue
            if i - s < sr3_window:
                nw.append((side, L, s, ext))
        watch = nw
        L = hi_lv[i]
        if np.isfinite(L) and not used_hi and h[i] > L + dlt:
            used_hi = True
            if c[i] < L:
                ev.append(Event(i, -1, h[i] + stop_k * a, "A1_SR1", family, L))
            else:
                if c[i] > L + dlt:
                    ev.append(Event(i, +1, np.nan, "A2_BO", family, L))     # stop set at entry (entry - 0.5 ATR)
                watch.append((+1, L, i, h[i]))
        L = lo_lv[i]
        if np.isfinite(L) and not used_lo and l[i] < L - dlt:
            used_lo = True
            if c[i] > L:
                ev.append(Event(i, +1, l[i] - stop_k * a, "A1_SR1", family, L))
            else:
                if c[i] < L - dlt:
                    ev.append(Event(i, -1, np.nan, "A2_BO", family, L))
                watch.append((-1, L, i, l[i]))
    for e in ev:
        if e.strategy == "A2_BO":
            e.stop = bo_stop_k * atr[e.i]          # placeholder: distance, converted at entry
    return ev


def simulate(df: pd.DataFrame, events: list[Event], cost_fn, hold: int = 6, target_r: float | None = None) -> pd.DataFrame:
    """One trade at a time per (strategy, family). Conservative intrabar ordering: stop first."""
    o, h, l = df.open.to_numpy(), df.high.to_numpy(), df.low.to_numpy()
    n = len(o); rows = []; busy_until = -1
    for e in sorted(events, key=lambda x: x.i):
        if e.i <= busy_until or e.i + 1 >= n:
            continue
        k0 = e.i + 1; entry = o[k0]; d = e.direction
        stop = entry - d * e.stop if e.strategy == "A2_BO" else e.stop
        risk = d * (entry - stop)
        if not np.isfinite(risk) or risk <= 0:
            continue                                   # gapped through the stop before entry: no trade
        tgt = entry + d * target_r * risk if target_r else None
        exit_px, exit_k, why = None, None, "time"
        last = min(k0 + hold, n - 1)
        for k in range(k0, last):
            if d > 0 and l[k] <= stop:
                exit_px, exit_k, why = min(stop, o[k]), k, "stop"; break
            if d < 0 and h[k] >= stop:
                exit_px, exit_k, why = max(stop, o[k]), k, "stop"; break
            if tgt is not None and ((d > 0 and h[k] >= tgt) or (d < 0 and l[k] <= tgt)):
                exit_px, exit_k, why = (max(tgt, o[k]) if d > 0 else min(tgt, o[k])), k, "target"; break
        if exit_px is None:
            exit_k = last; exit_px = o[last]
        cost = cost_fn(entry)
        gross = d * (exit_px - entry)
        rows.append({"t_signal": df.index[e.i], "t_entry": df.index[k0], "t_exit": df.index[exit_k], "strategy": e.strategy, "family": e.family,
                     "dir": d, "entry": entry, "stop": stop, "exit": exit_px, "why": why, "risk": risk,
                     "R_gross": gross / risk, "R_net": (gross - cost) / risk, "cost_R": cost / risk})
        busy_until = exit_k
    return pd.DataFrame(rows)


def daily_series(trades: pd.DataFrame, calendar: pd.DatetimeIndex, col: str = "R_net") -> pd.Series:
    if trades.empty:
        return pd.Series(0.0, index=calendar)
    s = trades.groupby(trades.t_exit.dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None))[col].sum()
    return s.reindex(calendar, fill_value=0.0)


def summarize(trades: pd.DataFrame, daily: pd.Series, ann: float, daily_gross: pd.Series | None = None) -> dict:
    if trades.empty:
        return {"trades": 0}
    r = trades.R_net
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    ret = daily * RISK_PER_TRADE
    eq = (1 + ret).cumprod()
    years = max(len(daily) / ann, 1e-9)
    cagr = float(eq.iloc[-1] ** (1 / years) - 1)
    mdd = float((eq / eq.cummax() - 1).min())
    sh = float(daily.mean() / daily.std() * np.sqrt(ann)) if daily.std() > 0 else 0.0
    out = {"trades": int(len(r)), "expectancy_R_net": float(r.mean()), "expectancy_R_gross": float(trades.R_gross.mean()),
           "win_rate": float((r > 0).mean()), "profit_factor_net": float(pos / neg) if neg > 0 else None,
           "avg_win_R": float(r[r > 0].mean()) if (r > 0).any() else None, "avg_loss_R": float(r[r < 0].mean()) if (r < 0).any() else None,
           "cost_share_of_gross": float(trades.cost_R.sum() / trades.R_gross.clip(lower=0).sum()) if trades.R_gross.clip(lower=0).sum() > 0 else None,
           "sharpe_net": sh, "cagr_at_0.25pct_risk": cagr, "vol_at_0.25pct_risk": float(ret.std() * np.sqrt(ann)), "max_dd_at_0.25pct_risk": mdd,
           "calmar": float(cagr / abs(mdd)) if mdd < 0 else None, "long_exp_R": float(r[trades.dir > 0].mean()) if (trades.dir > 0).any() else None,
           "short_exp_R": float(r[trades.dir < 0].mean()) if (trades.dir < 0).any() else None, "n_long": int((trades.dir > 0).sum()),
           "stop_exits": float((trades.why == "stop").mean())}
    if daily_gross is not None and daily_gross.std() > 0:
        out["sharpe_gross"] = float(daily_gross.mean() / daily_gross.std() * np.sqrt(ann))
    return out


def daily_mtm(df: pd.DataFrame, trades: pd.DataFrame, cost_fn) -> pd.Series:
    """Mark-to-market P&L in R per bar for multi-bar trades (bar = day for daily data). Sums exactly to R_net per trade.
    (daily_series books a trade's whole P&L on its exit bar - fine for sub-day trades, wrong for beta/correlation/vol of
    multi-day holds.)"""
    c = df.close.to_numpy(); pos = {t: i for i, t in enumerate(df.index)}
    pnl = np.zeros(len(c))
    for tr in trades.itertuples():
        k0, ke = pos[tr.t_entry], pos[tr.t_exit]
        d, unit = tr.dir, 1.0 / tr.risk
        pnl[k0] -= cost_fn(tr.entry) * unit
        if ke == k0:
            pnl[k0] += d * (tr.exit - tr.entry) * unit; continue
        pnl[k0] += d * (c[k0] - tr.entry) * unit
        for k in range(k0 + 1, ke):
            pnl[k] += d * (c[k] - c[k - 1]) * unit
        pnl[ke] += d * (tr.exit - c[ke - 1]) * unit
    return pd.Series(pnl, index=df.index)
