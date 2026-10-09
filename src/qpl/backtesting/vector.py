"""Position-based backtester for 24/7 markets (crypto).

Convention (no look-ahead by construction):
  w[t]   target position (fraction of equity, signed) decided with information up to the CLOSE of bar t
  fill   at OPEN of bar t+1;   held until the open of bar t+2 (or until changed)
  r[t+1] = open[t+2] / open[t+1] - 1   (return earned by w[t])
Costs: |w[t] - w[t-1]| * cost_bps per unit turnover (fees + half spread + slippage).
Funding (perpetuals): position held across a settlement pays/receives  -w * rate  (long pays positive funding).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run(bars: pd.DataFrame, w: pd.Series, cost_bps: float = 7.0, funding: pd.Series | None = None,
        perp: bool = True) -> pd.DataFrame:
    o = bars["open"].to_numpy(float)
    w = w.reindex(bars.index).fillna(0.0).to_numpy(float)
    n = len(o)
    ret_next = np.full(n, np.nan)
    ret_next[:-2] = o[2:] / o[1:-1] - 1.0                  # earned by w[t]
    gross = w * ret_next
    turnover = np.abs(np.diff(np.r_[0.0, w]))
    cost = turnover * cost_bps / 1e4
    fund = np.zeros(n)
    if perp and funding is not None and len(funding):
        # settlement s is earned by the position held over [open t+1, open t+2) containing s
        idx = bars.index
        start = idx[1:]                                     # holding interval start = open of t+1
        f = funding.sort_index()
        # audit V4-B1: align datetime units explicitly (pandas 3 mixes us/ns; raw asi8 comparison is wrong)
        pos_of = np.searchsorted(idx.as_unit("ns").asi8, f.index.as_unit("ns").asi8, side="right") - 2
        ok = (pos_of >= 0) & (pos_of < n)
        np.add.at(fund, pos_of[ok], -w[pos_of[ok]] * f.to_numpy()[ok])
    net = np.nan_to_num(gross) - cost + fund
    out = pd.DataFrame({"w": w, "gross": np.nan_to_num(gross), "cost": cost, "funding": fund, "net": net,
                        "turnover": turnover}, index=bars.index)
    out.loc[out.index[-2:], ["gross", "net"]] = 0.0
    return out


def daily(res: pd.DataFrame) -> pd.DataFrame:
    return res[["gross", "cost", "funding", "net", "turnover"]].resample("1D").sum()


def vol_target(signal: pd.Series, bars: pd.DataFrame, target_ann: float = 0.4, lookback_bars: int = 30,
               bars_per_year: float = 365.0, cap: float = 1.0) -> pd.Series:
    """Scale a {-1,0,1} signal to a target annualized vol using trailing realized vol (known at t)."""
    r = np.log(bars["close"]).diff()
    vol = r.rolling(lookback_bars, min_periods=lookback_bars // 2).std() * np.sqrt(bars_per_year)
    return (signal * (target_ann / vol)).clip(-cap, cap)


def stats(d: pd.Series) -> dict:
    d = d.dropna()
    if len(d) < 2 or d.std() == 0:
        return {"sharpe": 0.0, "ann_ret": 0.0, "ann_vol": 0.0, "max_dd": 0.0, "days": len(d)}
    eq = d.cumsum()
    return {"sharpe": float(d.mean() / d.std() * np.sqrt(365)), "ann_ret": float(d.mean() * 365),
            "ann_vol": float(d.std() * np.sqrt(365)), "max_dd": float((eq - eq.cummax()).min()),
            "worst_day": float(d.min()), "days": int(len(d)),
            "cvar5": float(d[d <= d.quantile(0.05)].mean())}
