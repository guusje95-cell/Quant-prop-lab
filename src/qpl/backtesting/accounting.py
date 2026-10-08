"""Trade list (points) -> USD P&L with position sizing and cost stress."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..instruments import Instrument


def size_trades(tr: pd.DataFrame, inst: Instrument, risk_usd: float | None = None, contracts: int | None = None,
                max_contracts: int = 50, min_contracts: int = 1) -> np.ndarray:
    """Contracts per trade. Risk-based sizing uses the stop distance known at entry
    (risk_pts) plus round-turn cost so the *planned* loss at the stop <= risk_usd."""
    if contracts is not None:
        return np.full(len(tr), contracts, dtype=np.int64)
    per = tr["risk_pts"].to_numpy() * inst.point_value + inst.cost_per_rt()
    with np.errstate(invalid="ignore", divide="ignore"):
        q = np.floor(risk_usd / per)
    q = np.where(np.isfinite(q), q, 0)
    q = np.clip(q, 0, max_contracts).astype(np.int64)
    q[q < min_contracts] = 0          # trade skipped if risk budget cannot afford 1 contract
    return q


def to_usd(tr: pd.DataFrame, inst: Instrument, qty: np.ndarray, cost_mult: float = 1.0, slip_mult: float = 1.0,
           base_slip_ticks: float | None = None) -> pd.DataFrame:
    """Add USD columns. The engine is run frictionless (slip_ticks=0); ALL slippage is applied
    here: base_slip_ticks (default inst.slippage_ticks) * slip_mult ticks per slipped side.
    Entries (market/stop) are always slipped; exits are slipped unless filled by a limit target."""
    base = inst.slippage_ticks if base_slip_ticks is None else base_slip_ticks
    out = tr.copy()
    out["qty"] = qty
    pv = inst.point_value
    sides = 1 + (out["reason"].to_numpy() != 2).astype(float)
    slip_pts = slip_mult * base * inst.tick_size * sides
    comm = cost_mult * inst.commission_rt
    out["pnl_usd"] = qty * ((out["pnl_pts"] - slip_pts) * pv - comm)
    # worst open P&L: MAE plus entry+exit slippage and commission (liquidation at the worst point)
    out["mae_usd"] = qty * ((np.minimum(out["mae_pts"], 0) - slip_mult * base * inst.tick_size * 2) * pv - comm)
    out["cost_usd"] = qty * (comm + slip_pts * pv)
    out = out[out["qty"] > 0].copy()
    return out


def daily_pnl(trades: pd.DataFrame, all_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily realized P&L + worst intraday equity (relative to prior close) per trading day.

    One position at a time => worst intraday point of a day = min over the day's
    trades of (realized P&L before the trade + that trade's MAE)."""
    days = pd.DatetimeIndex(trades["day"]) if len(trades) else pd.DatetimeIndex([])
    pnl = np.zeros(len(all_days))
    worst = np.zeros(len(all_days))
    ntr = np.zeros(len(all_days), dtype=np.int64)
    pos = {d: i for i, d in enumerate(all_days)}
    if len(trades):
        for d, g in trades.groupby(days):
            i = pos.get(d)
            if i is None:
                continue
            p = g["pnl_usd"].to_numpy()
            m = g["mae_usd"].to_numpy()
            before = np.concatenate([[0.0], np.cumsum(p)[:-1]])
            pnl[i] = p.sum()
            worst[i] = min(0.0, float(np.min(before + m)), float(np.min(np.cumsum(p))))
            ntr[i] = len(g)
    return pd.DataFrame({"pnl": pnl, "worst": worst, "ntrades": ntr}, index=all_days)
