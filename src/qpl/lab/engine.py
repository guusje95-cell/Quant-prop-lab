"""Backtest Lab engine: signals -> sized weights -> P&L with costs, funding and intrabar extremes.

Timing: a weight decided at the close of bar t is held over bar t+1 (close-to-close return), so there is no look-ahead
as long as the strategy only uses data up to t. Costs are charged on turnover at the start of the bar in which the trade
happens. Intrabar worst/best use each asset's high/low vs the previous close, assuming every asset is at its worst at the
same moment (conservative), which is what equity-based prop-firm daily-loss rules care about."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Config:
    cost_bps: float = 7.5             # per unit of turnover (one side): fee + slippage, e.g. Bybit taker 5.5 + 2 bp
    funding_bps_day: float = 0.0      # paid by longs / received by shorts per day of exposure (0 at CFT Bybit route)
    asset_vol_target: float = 0.40    # per-asset volatility scaling target (annual); 0 disables vol scaling
    vol_lookback_days: int = 30
    max_asset_weight: float = 1.0     # cap per asset after vol scaling (before leverage)
    leverage: float = 1.0             # final multiplier on the whole book
    min_history_days: int = 200       # an asset is tradable only after this many days of data


def size(bars, sig: pd.DataFrame, cfg: Config, sizing="engine") -> pd.DataFrame:
    sig = sig.reindex(index=bars.close.index, columns=bars.symbols).fillna(0).clip(-2, 2)   # [-1,1] normal; up to 2 = conviction scaling
    if sizing == "raw":
        return sig * cfg.leverage
    bpd = {"1h": 24, "4h": 6}.get(bars.freq, 1)
    ppy = bars.periods_per_year
    lr = np.log(bars.close).diff()
    n = cfg.vol_lookback_days * bpd
    vol = lr.rolling(n, min_periods=max(5, int(n * 0.66))).std() * np.sqrt(ppy)
    hist = bars.close.notna().cumsum() >= cfg.min_history_days * bpd
    scale = (cfg.asset_vol_target / vol).clip(upper=cfg.max_asset_weight) if cfg.asset_vol_target > 0 else 1.0
    w = (sig * scale).where(hist, 0.0)
    nact = hist.sum(axis=1).replace(0, np.nan)
    return w.div(nact, axis=0).fillna(0) * cfg.leverage


def run(bars, weights: pd.DataFrame, cfg: Config) -> dict:
    c = bars.close
    ret = c.pct_change(fill_method=None).fillna(0)
    wp = weights.shift(1).fillna(0)                                  # held during bar t
    turn = wp.diff().abs().fillna(wp.abs())
    bpd = {"1h": 24, "4h": 6}.get(bars.freq, 1)
    cost = turn.sum(axis=1) * cfg.cost_bps / 1e4
    fund = (wp.sum(axis=1)) * cfg.funding_bps_day / 1e4 / bpd
    gross = (wp * ret).sum(axis=1)
    lo = (bars.low / c.shift(1) - 1).fillna(0); hi = (bars.high / c.shift(1) - 1).fillna(0)
    worst = (wp.clip(lower=0) * lo + wp.clip(upper=0) * hi).sum(axis=1) - cost
    best = (wp.clip(lower=0) * hi + wp.clip(upper=0) * lo).sum(axis=1) - cost
    res = pd.DataFrame({"gross": gross, "cost": cost, "funding": -fund, "net": gross - cost - fund, "worst": worst, "best": best,
                        "gross_exposure": wp.abs().sum(axis=1), "net_exposure": wp.sum(axis=1), "turnover": turn.sum(axis=1)})
    contrib = (wp * ret).sub(turn * cfg.cost_bps / 1e4)
    return {"bars": res, "weights": weights, "held": wp, "asset_pnl": contrib}


def to_daily(res: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Aggregate bar results to UTC days; intraday worst/best follow the path within the day (vs equity at 00:00)."""
    if freq == "1d":
        return res[["net", "gross", "cost", "funding", "worst", "best"]].copy()
    day = res.index.floor("D")
    out = []
    for d, g in res.groupby(day):
        r = g["net"].to_numpy()
        cum = np.concatenate([[1.0], np.cumprod(1 + r)])
        out.append((d, cum[-1] - 1, float(np.prod(1 + g["gross"].to_numpy()) - 1), g["cost"].sum(), g["funding"].sum(),
                    float(np.min(cum[:-1] * (1 + g["worst"].to_numpy())) - 1), float(np.max(cum[:-1] * (1 + g["best"].to_numpy())) - 1)))
    return pd.DataFrame(out, columns=["day", "net", "gross", "cost", "funding", "worst", "best"]).set_index("day")


def trades(held: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    """Round trips per asset: a trade opens when the position leaves 0 (or flips sign) and closes when it returns/flips."""
    rows = []
    ret = close.pct_change(fill_method=None).fillna(0)
    for s in held.columns:
        w = held[s].to_numpy(); r = ret[s].to_numpy(); idx = held.index
        cur, start, pnl = 0.0, None, 0.0
        for t in range(len(w)):
            sgn = np.sign(w[t])
            if cur != 0 and sgn != cur:
                rows.append((s, idx[start], idx[t - 1], "long" if cur > 0 else "short", t - start, pnl)); cur, start, pnl = 0.0, None, 0.0
            if sgn != 0 and cur == 0:
                cur, start, pnl = sgn, t, 0.0
            if cur != 0:
                pnl += w[t] * r[t]
        if cur != 0:
            rows.append((s, idx[start], idx[len(w) - 1], "long" if cur > 0 else "short", len(w) - start, pnl))
    return pd.DataFrame(rows, columns=["asset", "entry", "exit", "side", "bars", "pnl_contribution"])
