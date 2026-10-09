"""F9_SLEEVE_RP (config/f9_spec.json): equal-risk trend + carry futures book. Used by both the historical record and the paper engine."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtesting import panel as PB
from . import futures_factors as FF


def sleeve_signals(ret: pd.DataFrame, carry_yield: pd.DataFrame) -> dict[str, pd.DataFrame]:
    trend = ((FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0)) / 3).where(ret.notna().cumsum() > 0)
    return {"TREND": trend, "CARRY": FF.carry(ret, carry_yield, 21)}


def buffer_weights(W: pd.DataFrame, b: float = 0.05) -> pd.DataFrame:
    m = W.abs().rolling(252, min_periods=20).mean().fillna(W.abs()).to_numpy()
    w = W.to_numpy(); out = np.zeros_like(w); held = np.zeros(w.shape[1])
    for t in range(len(w)):
        lo, hi = held - b * m[t], held + b * m[t]
        tgt = w[t]
        held = np.where(tgt < lo, tgt + b * m[t], np.where(tgt > hi, tgt - b * m[t], held))
        held = np.where(tgt == 0, 0.0, held)
        out[t] = held
    return pd.DataFrame(out, index=W.index, columns=W.columns)


def weights(ret: pd.DataFrame, cost: pd.DataFrame, carry_yield: pd.DataFrame, b: float = 0.05, book_vol: float = 0.10, lag: int = 2) -> pd.DataFrame:
    sig = PB.sigma(ret)
    Ws = []
    for s in sleeve_signals(ret, carry_yield).values():
        _, W = PB.run(ret, s, cost, sig=sig, return_weights=True, lag=lag)
        Ws.append(W)
    W = 0.5 * Ws[0] + 0.5 * Ws[1]
    raw = (W.shift(lag) * ret.fillna(0)).sum(axis=1)
    rv = raw.rolling(252, min_periods=63).std() * np.sqrt(PB.ANN)
    k = (book_vol / rv).clip(upper=2.0).fillna(0.0)
    return buffer_weights(W.mul(k, axis=0), b)


def pnl(ret: pd.DataFrame, cost: pd.DataFrame, W: pd.DataFrame, lag: int = 2, cost_mult: float = 1.0) -> pd.DataFrame:
    r0 = ret.fillna(0.0)
    gross = (W.shift(lag) * r0).sum(axis=1)
    turn = (W.shift(lag - 1) - W.shift(lag)).abs()
    cst = (turn * cost.reindex_like(W).ffill().shift(lag - 1)).sum(axis=1) * cost_mult
    return pd.DataFrame({"gross": gross, "cost": cst, "net": gross - cst, "turnover": turn.sum(axis=1), "gross_lev": W.abs().sum(axis=1)})
