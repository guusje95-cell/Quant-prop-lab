"""Backtest Lab analysis: performance metrics, edge diagnostics (is it real?), and prop-firm simulation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as st

from qpl.prop_simulation import cft_daily as CFT
from qpl.prop_simulation.cft_ledger import run_ledger


# ------------------------------------------------------------------ performance
def summary(net: pd.Series, ppy: float) -> dict:
    x = net.dropna()
    if len(x) < 5 or x.std() == 0:
        return {}
    eq = (1 + x).cumprod(); dd = eq / eq.cummax() - 1
    years = len(x) / ppy
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    vol = x.std() * np.sqrt(ppy)
    downside = x[x < 0].std() * np.sqrt(ppy)
    m = (1 + x).resample("ME").prod() - 1
    return {"Total return": eq.iloc[-1] - 1, "CAGR": cagr, "Volatility": vol, "Sharpe": x.mean() / x.std() * np.sqrt(ppy),
            "Sortino": x.mean() * ppy / downside if downside > 0 else np.nan, "Max drawdown": dd.min(),
            "Calmar": cagr / -dd.min() if dd.min() < 0 else np.nan, "Positive months": (m > 0).mean(), "Worst month": m.min(),
            "Best month": m.max(), "Worst bar": x.min(), "Skew": st.skew(x), "Years": years}


def drawdown(net):
    eq = (1 + net.fillna(0)).cumprod(); return eq / eq.cummax() - 1


def monthly_table(net):
    m = (1 + net.fillna(0)).resample("ME").prod() - 1
    t = pd.DataFrame({"year": m.index.year, "month": m.index.month, "r": m.values}).pivot(index="year", columns="month", values="r")
    t["Year"] = (1 + net.fillna(0)).groupby(net.index.year).prod() - 1
    return t


def rolling_sharpe(net, ppy, window_days=365, bpd=1):
    w = int(window_days * bpd)
    return net.rolling(w, min_periods=w // 2).mean() / net.rolling(w, min_periods=w // 2).std() * np.sqrt(ppy)


# ------------------------------------------------------------------ edge diagnostics
def bootstrap_sharpe(net, ppy, n=2000, block=20, seed=0):
    """Stationary bootstrap (random block lengths, mean `block`) of the annualised Sharpe; vectorised over the series."""
    x = net.dropna().to_numpy(); T = len(x); rng = np.random.default_rng(seed)
    p = 1.0 / block; out = np.empty(n); pos = np.arange(T)
    for k in range(n):
        new = rng.random(T) < p; new[0] = True                         # where a new block starts
        starts = rng.integers(0, T, size=T)
        first = np.maximum.accumulate(np.where(new, pos, 0))            # index where the current block began
        idx = (starts[first] + pos - first) % T
        y = x[idx]; sd = y.std(); out[k] = y.mean() / sd * np.sqrt(ppy) if sd > 0 else 0
    return np.percentile(out, [2.5, 50, 97.5]), out


def psr(net, ppy, sr_bench_ann=0.0):
    x = net.dropna().to_numpy(); n = len(x); sr = x.mean() / x.std()
    srb = sr_bench_ann / np.sqrt(ppy); g3, g4 = st.skew(x), st.kurtosis(x, fisher=False)
    return float(st.norm.cdf((sr - srb) * np.sqrt(n - 1) / np.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))))


def dsr(net, ppy, n_trials):
    """Deflated Sharpe: probability the Sharpe beats the best of n_trials pure-noise strategies."""
    x = net.dropna().to_numpy(); n = len(x)
    if n_trials <= 1:
        return psr(net, ppy)
    emc = 0.5772156649; v = 1.0 / n
    sr0 = np.sqrt(v) * ((1 - emc) * st.norm.ppf(1 - 1 / n_trials) + emc * st.norm.ppf(1 - 1 / (n_trials * np.e)))
    return psr(net, ppy, sr0 * np.sqrt(ppy))


def split_stats(net, ppy, split_date):
    a, b = net.loc[:split_date], net.loc[split_date:]
    return summary(a, ppy), summary(b, ppy)


def random_timing_pvalue(weights_held, ret, ppy, n=300, seed=1):
    """Shuffle the strategy's position path in blocks (keeps exposure, destroys timing). p = share of random paths with a
    Sharpe >= the real one. Low p = the timing itself carries information."""
    rng = np.random.default_rng(seed)
    real = (weights_held * ret).sum(axis=1); sr_real = real.mean() / real.std() * np.sqrt(ppy)
    W = weights_held.to_numpy(); R = ret.to_numpy(); T = len(W); blk = 20; cnt = 0
    for _ in range(n):
        starts = rng.integers(0, T, size=T // blk + 1)
        idx = np.concatenate([np.arange(s, s + blk) % T for s in starts])[:T]
        x = (W[idx] * R).sum(axis=1)
        if x.std() > 0 and x.mean() / x.std() * np.sqrt(ppy) >= sr_real:
            cnt += 1
    return (cnt + 1) / (n + 1), sr_real


# ------------------------------------------------------------------ prop firm
PROGRAMS = {"CFT 1-Phase (10% target, 4% daily, 6% trailing)": "1PHASE", "CFT 2-Phase (8%+5%, 5% daily, 10% static)": "2PHASE"}


def prop_attempts(daily: pd.DataFrame, program: str, scale: float, start=None, end=None, step=3, max_days=548):
    r = (daily["net"] * scale).to_numpy(); lo = (daily["worst"] * scale).to_numpy(); hi = (daily["best"] * scale).to_numpy()
    idx = daily.index
    s0 = pd.Timestamp(start) if start else idx[0]; s1 = pd.Timestamp(end) if end else idx[-1] - pd.Timedelta(days=180)
    starts = [i for i in range(0, len(idx), step) if s0 <= idx[i] <= s1]
    res = [CFT.simulate_start(r, s, program, mode="optimistic", max_days=max_days, lo=lo, hi=hi) for s in starts]
    out = CFT.summarize(res)
    out["starts"] = [idx[s] for s in starts]; out["results"] = [x["result"] for x in res]
    return out


def prop_pipeline(daily_ch: pd.DataFrame, daily_fd: pd.DataFrame, program: str, scale_c: float, scale_f: float, account: float,
                  fee: float, budget: int, horizon=730, step=5):
    rc = tuple((daily_ch[k] * scale_c).to_numpy() for k in ("net", "worst", "best"))
    j = daily_fd.reindex(daily_ch.index).fillna(0)
    rf = tuple((j[k] * scale_f).to_numpy() for k in ("net", "worst", "best"))
    starts = list(range(0, max(1, len(daily_ch) - horizon), step))
    runs = [run_ledger(*rc, *rf, s, program, account, fee, budget, horizon) for s in starts]
    W = np.vstack([np.pad(r["wealth"], (0, horizon - len(r["wealth"])), "edge") for r in runs])
    net = np.array([r["net"] for r in runs])
    return {"n": len(runs), "P_funded": float(np.mean([r["passed"] > 0 for r in runs])), "bought": float(np.mean([r["bought"] for r in runs])),
            "fees": float(np.mean([r["fees"] for r in runs])), "paid": float(np.mean([r["paid"] for r in runs])),
            "net_mean": float(net.mean()), "net_p10": float(np.percentile(net, 10)), "net_p50": float(np.percentile(net, 50)),
            "net_p90": float(np.percentile(net, 90)), "P_profit": float((net > 0).mean()),
            "curve": pd.DataFrame({"p10": np.percentile(W, 10, axis=0), "p50": np.percentile(W, 50, axis=0),
                                   "p90": np.percentile(W, 90, axis=0), "mean": W.mean(axis=0)})}
