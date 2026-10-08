"""Performance metrics computed from a daily P&L series (USD) and trade list."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as st

ANN = 252


def drawdown(equity: np.ndarray) -> np.ndarray:
    peak = np.maximum.accumulate(equity)
    return equity - peak


def streaks(x: np.ndarray) -> tuple[int, int]:
    """Longest winning and losing streak in a sequence of trade P&Ls."""
    best_w = best_l = cw = cl = 0
    for v in x:
        if v > 0:
            cw += 1; cl = 0
        elif v < 0:
            cl += 1; cw = 0
        best_w = max(best_w, cw); best_l = max(best_l, cl)
    return best_w, best_l


def dd_durations(equity: np.ndarray) -> np.ndarray:
    peak = np.maximum.accumulate(equity)
    under = equity < peak - 1e-9
    durs, cur = [], 0
    for u in under:
        if u:
            cur += 1
        elif cur:
            durs.append(cur); cur = 0
    if cur:
        durs.append(cur)
    return np.array(durs) if durs else np.array([0])


def summarize(daily: pd.Series, trades: pd.DataFrame | None = None, capital: float = 50_000.0) -> dict:
    """daily: USD P&L per trading day (zeros on no-trade days)."""
    x = daily.to_numpy(float)
    n = len(x)
    eq = np.cumsum(x)
    dd = drawdown(np.concatenate([[0.0], eq]))[1:]
    mu, sd = x.mean(), x.std(ddof=1) if n > 1 else 0.0
    down = x[x < 0]
    dsd = np.sqrt(np.mean(np.minimum(x, 0) ** 2)) if n else 0.0
    years = n / ANN
    total = eq[-1] if n else 0.0
    maxdd = -dd.min() if n else 0.0
    out = {
        "days": n, "years": round(years, 2), "total_usd": total,
        "ann_return_usd": mu * ANN, "ann_return_pct_cap": mu * ANN / capital,
        "ann_vol_usd": sd * np.sqrt(ANN),
        "sharpe": (mu / sd * np.sqrt(ANN)) if sd > 0 else np.nan,
        "sortino": (mu / dsd * np.sqrt(ANN)) if dsd > 0 else np.nan,
        "max_dd_usd": maxdd, "avg_dd_usd": float(-dd[dd < 0].mean()) if (dd < 0).any() else 0.0,
        "calmar": (mu * ANN / maxdd) if maxdd > 0 else np.nan,
        "max_dd_duration_days": int(dd_durations(np.concatenate([[0.0], eq])).max()),
        "skew_daily": float(st.skew(x)) if n > 2 else np.nan,
        "kurt_daily": float(st.kurtosis(x)) if n > 3 else np.nan,
        "worst_day": float(x.min()) if n else 0.0, "best_day": float(x.max()) if n else 0.0,
        "pct_days_traded": float(np.mean(x != 0)) if n else 0.0,
        "return_over_maxdd": total / maxdd if maxdd > 0 else np.nan,
    }
    if trades is not None and len(trades):
        p = trades["pnl_usd"].to_numpy()
        w, lo = p[p > 0], p[p < 0]
        sw, sl = streaks(p)
        out.update({
            "trades": int(len(p)), "trades_per_year": len(p) / years if years > 0 else np.nan,
            "win_rate": float(np.mean(p > 0)),
            "avg_win": float(w.mean()) if len(w) else 0.0, "avg_loss": float(lo.mean()) if len(lo) else 0.0,
            "expectancy_usd": float(p.mean()),
            "profit_factor": float(w.sum() / -lo.sum()) if len(lo) and lo.sum() < 0 else np.nan,
            "max_win_streak": sw, "max_loss_streak": sl,
            "avg_hold_bars": float((trades["exit_i"] - trades["entry_i"]).mean()),
            "total_cost_usd": float(trades["cost_usd"].sum()) if "cost_usd" in trades else np.nan,
        })
        if "cost_usd" in trades and trades["cost_usd"].sum() > 0:
            out["return_per_cost"] = total / trades["cost_usd"].sum()
        if "risk_pts" in trades and "pnl_pts" in trades:
            r = (trades["pnl_pts"] / trades["risk_pts"]).replace([np.inf, -np.inf], np.nan).dropna()
            out["avg_R"] = float(r.mean()) if len(r) else np.nan
    return out


def yearly(daily: pd.Series) -> pd.Series:
    return daily.groupby(daily.index.year).sum()


def monthly(daily: pd.Series) -> pd.Series:
    return daily.groupby([daily.index.year, daily.index.month]).sum()


def rolling_sharpe(daily: pd.Series, window: int = 126) -> pd.Series:
    m = daily.rolling(window).mean()
    s = daily.rolling(window).std()
    return m / s * np.sqrt(ANN)
