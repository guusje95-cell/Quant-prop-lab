"""Standard performance metrics on a DAILY return series (fractions of equity, calendar days, crypto convention 365 days a year;
pass periods_per_year=252 for exchange-traded futures). One methodology everywhere; every result states its sample."""
from __future__ import annotations

import numpy as np
import pandas as pd


def to_daily(r: pd.Series) -> pd.Series:
    """Hourly (or finer) returns -> daily sums by UTC day (additive, as everywhere in this project)."""
    r = r.dropna()
    if len(r) and (pd.Series(r.index).diff().median() < pd.Timedelta(hours=23)):
        return r.groupby(r.index.floor("D")).sum()
    return r


def drawdown(r: pd.Series, compounding: bool = True) -> pd.Series:
    eq = (1 + r).cumprod() if compounding else r.cumsum() + 1
    return eq / eq.cummax() - 1


def summary(r: pd.Series, periods_per_year: int = 365, trades: pd.Series | None = None, benchmark: pd.Series | None = None) -> dict:
    d = to_daily(r)
    if len(d) < 2 or d.std() == 0:
        return {"status": "insufficient data", "days": int(len(d))}
    n = len(d); yrs = n / periods_per_year
    mu, sd = d.mean(), d.std(ddof=1)
    eq = (1 + d).cumprod(); dd = eq / eq.cummax() - 1
    under = (dd < 0).astype(int); runs = under.groupby((under == 0).cumsum()).sum()
    neg = d[d < 0]
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else -1.0
    out = {"status": "ok", "start": str(d.index[0].date()), "end": str(d.index[-1].date()), "days": int(n),
           "total_return": float(eq.iloc[-1] - 1), "cagr": cagr, "ann_return_arith": float(mu * periods_per_year),
           "ann_vol": float(sd * np.sqrt(periods_per_year)), "sharpe": float(mu / sd * np.sqrt(periods_per_year)),
           "sortino": float(mu / np.sqrt((np.minimum(d, 0) ** 2).mean()) * np.sqrt(periods_per_year)) if len(neg) else None,
           "max_drawdown": float(dd.min()), "max_dd_days": int(runs.max()) if len(runs) else 0,
           "calmar": float(cagr / abs(dd.min())) if dd.min() < 0 else None,
           "pct_positive_days": float((d > 0).mean()), "worst_day": float(d.min()), "best_day": float(d.max()),
           "var_95_day": float(-np.percentile(d, 5)), "cvar_95_day": float(-d[d <= np.percentile(d, 5)].mean()),
           "skew": float(d.skew()), "kurtosis": float(d.kurt() + 3),
           "by_year": {str(y): _sh(g, periods_per_year) for y, g in d.groupby(d.index.year)},
           "sharpe_method": f"mean / sd of daily returns x sqrt({periods_per_year}); daily = sum of the day's returns"}
    if trades is not None and len(trades):
        t = trades.dropna(); w, l = t[t > 0], t[t < 0]
        out.update({"trades": int(len(t)), "win_rate": float((t > 0).mean()), "avg_win": float(w.mean()) if len(w) else None,
                    "avg_loss": float(l.mean()) if len(l) else None, "profit_factor": float(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else None,
                    "expectancy": float(t.mean())})
    if benchmark is not None:
        b = to_daily(benchmark).reindex(d.index).fillna(0.0)
        beta = float(np.cov(d, b)[0, 1] / b.var()) if b.var() > 0 else None
        out.update({"benchmark_sharpe": _sh(b, periods_per_year), "beta": beta, "corr_benchmark": float(d.corr(b))})
    return out


def _sh(d: pd.Series, ppy: int):
    return round(float(d.mean() / d.std() * np.sqrt(ppy)), 3) if len(d) > 2 and d.std() > 0 else None


def sharpe(d: pd.Series, ppy: int = 365) -> float:
    d = to_daily(d); return float(d.mean() / d.std(ddof=1) * np.sqrt(ppy)) if len(d) > 2 and d.std() > 0 else float("nan")
