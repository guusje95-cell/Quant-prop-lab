"""Daily multi-instrument futures backtester (V6). Spec: config/v6_futures_protocol.json["engine"].

  sigma_i,t   EWMA(span 35) std of r_i through t (annualised sqrt(256)), floored at the 5th percentile of its own
              trailing ~5y history (known at t)
  eligible    >= 256 return observations through t, sigma and signal defined
  w_i,t       s_i,t * (0.40 / sigma_i,t) / N_t
  book scale  k_t = 0.10 / realised vol (trailing 252 rows) of the unscaled book's P&L through t, capped at 5
  P&L_t       sum_i W_i,{t-2} * r_i,t     (decided at close t-2, traded at close t-1, held over day t)
  cost        |W_i,t-1 - W_i,t-2| * c_i,t-1, booked on day t-1 (the trade day)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ANN = 256.0


def sigma(ret: pd.DataFrame, span: int = 35, floor_q: float = 0.05, floor_win: int = 1280) -> pd.DataFrame:
    s = ret.ewm(span=span, min_periods=20, ignore_na=True).std() * np.sqrt(ANN)
    s = s.where(ret.notna().cumsum() > 0)
    floor = s.rolling(floor_win, min_periods=256).quantile(floor_q)
    return np.maximum(s, floor.fillna(0.0)).where(s.notna())


def eligible(ret: pd.DataFrame, min_hist: int = 256) -> pd.DataFrame:
    return ret.notna().cumsum() >= min_hist


def run(ret: pd.DataFrame, signal: pd.DataFrame, cost: pd.DataFrame | None = None, inst_target: float = 0.40,
        book_target: float = 0.10, cap: float = 5.0, lag: int = 2, cost_mult: float = 1.0, sig: pd.DataFrame | None = None,
        return_weights: bool = False) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    sig_ = sigma(ret) if sig is None else sig
    s = signal.reindex_like(ret).clip(-1, 1)
    ok = eligible(ret) & sig_.notna() & s.notna()
    n = ok.sum(axis=1).replace(0, np.nan)
    w = (s * inst_target / sig_).where(ok).div(n, axis=0).fillna(0.0)
    r0 = ret.fillna(0.0)
    raw_pnl = (w.shift(lag) * r0).sum(axis=1)
    rv = raw_pnl.rolling(252, min_periods=63).std() * np.sqrt(ANN)
    k = (book_target / rv).clip(upper=cap).fillna(0.0)
    W = w.mul(k, axis=0)
    gross = (W.shift(lag) * r0).sum(axis=1)
    turn = (W.shift(lag - 1) - W.shift(lag)).abs()
    c = (cost.reindex_like(ret).ffill().shift(lag - 1) if cost is not None else 0.0)
    cst = (turn * c).sum(axis=1) * cost_mult if cost is not None else gross * 0
    out = pd.DataFrame({"gross": gross, "cost": cst, "net": gross - cst, "turnover": turn.sum(axis=1), "n": n.fillna(0),
                        "gross_lev": W.abs().sum(axis=1)})
    return (out, W) if return_weights else out


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 20 or x.std() == 0:
        return {"sharpe": 0.0, "ann_ret": 0.0, "ann_vol": 0.0, "max_dd": 0.0, "days": len(x)}
    eq = x.cumsum()
    return {"sharpe": float(x.mean() / x.std() * np.sqrt(ANN)), "ann_ret": float(x.mean() * ANN), "ann_vol": float(x.std() * np.sqrt(ANN)),
            "max_dd": float((eq - eq.cummax()).min()), "skew": float(x.skew()), "worst_day": float(x.min()), "days": int(len(x)),
            "cvar5": float(x[x <= x.quantile(0.05)].mean())}


def residual(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    x, y = x.align(y, join="inner")
    if y.var() == 0 or x.std() == 0:
        return 0.0, 0.0
    b = float(np.cov(x, y)[0, 1] / y.var())
    return stats(x - b * y)["sharpe"], b
