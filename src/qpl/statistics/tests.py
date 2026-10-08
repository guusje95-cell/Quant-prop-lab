"""Statistical validation tools."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as st
import statsmodels.api as sm


def stationary_bootstrap_indices(n: int, n_boot: int, block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (n_boot x n)."""
    p = 1.0 / block
    idx = np.empty((n_boot, n), dtype=np.int64)
    starts = rng.integers(0, n, size=(n_boot, n))
    newblk = rng.random((n_boot, n)) < p
    idx[:, 0] = starts[:, 0]
    for t in range(1, n):
        idx[:, t] = np.where(newblk[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_ci(x: np.ndarray, stat=np.mean, n_boot: int = 2000, block: float = 5.0, alpha: float = 0.05,
                 seed: int = 0) -> tuple[float, float, float]:
    """Stationary block bootstrap CI. Returns (lo, hi, P(stat<=0))."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(len(x), n_boot, block, rng)
    bs = np.array([stat(x[i]) for i in idx])
    return float(np.quantile(bs, alpha / 2)), float(np.quantile(bs, 1 - alpha / 2)), float(np.mean(bs <= 0))


def sharpe(x: np.ndarray) -> float:
    s = np.std(x, ddof=1)
    return float(np.mean(x) / s * np.sqrt(252)) if s > 0 else 0.0


def newey_west_t(x: np.ndarray, lags: int | None = None) -> tuple[float, float]:
    """HAC t-stat and one-sided p-value for mean(x) > 0."""
    x = np.asarray(x, float)
    n = len(x)
    if lags is None:
        lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
    m = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    t = float(m.tvalues[0])
    return t, float(1 - st.norm.cdf(t))


def probabilistic_sharpe(x: np.ndarray, sr_bench_ann: float = 0.0) -> float:
    """PSR (Bailey & Lopez de Prado 2012) using daily data; benchmark annualized."""
    x = np.asarray(x, float)
    n = len(x)
    sr = np.mean(x) / np.std(x, ddof=1)
    g3, g4 = st.skew(x), st.kurtosis(x, fisher=False)
    srb = sr_bench_ann / np.sqrt(252)
    z = (sr - srb) * np.sqrt(n - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(st.norm.cdf(z))


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """Expected maximum of n_trials iid SR estimates (False Strategy Theorem), per-period units."""
    if n_trials <= 1:
        return 0.0
    emc = 0.5772156649
    z1 = st.norm.ppf(1 - 1.0 / n_trials)
    z2 = st.norm.ppf(1 - 1.0 / (n_trials * np.e))
    return float(np.sqrt(var_sr) * ((1 - emc) * z1 + emc * z2))


def deflated_sharpe(x: np.ndarray, n_trials: int, var_sr_trials: float | None = None) -> float:
    """Deflated Sharpe Ratio: PSR against the expected max SR under n_trials of pure noise.
    var_sr_trials: variance of per-period SR across trials (if None, use 1/n as under H0)."""
    x = np.asarray(x, float)
    n = len(x)
    if var_sr_trials is None:
        var_sr_trials = 1.0 / n
    sr0 = expected_max_sharpe(n_trials, var_sr_trials)
    return probabilistic_sharpe(x, sr0 * np.sqrt(252))


def whites_reality_check(R: np.ndarray, n_boot: int = 2000, block: float = 5.0, seed: int = 0) -> dict:
    """White (2000) Reality Check and Hansen (2005) SPA (consistent) p-values.
    R: (T x K) matrix of daily excess returns of K tested strategy variants vs a zero benchmark.
    H0: no variant has positive expected return."""
    R = np.asarray(R, float)
    T, K = R.shape
    rng = np.random.default_rng(seed)
    mu = R.mean(0)
    idx = stationary_bootstrap_indices(T, n_boot, block, rng)
    stat = np.sqrt(T) * mu.max()
    sd = R.std(0, ddof=1) * 1.0
    sd[sd == 0] = 1e-12
    # SPA consistent recentering
    # SPA_c: variants that are 'very bad' are recentred at zero, others at their mean
    mu_c = np.where(np.sqrt(T) * mu / sd <= -np.sqrt(2 * np.log(np.log(T))), 0.0, mu)
    spa_stat = max(0.0, np.max(np.sqrt(T) * mu / sd))
    rc, spa = 0, 0
    for i in idx:
        mb = R[i].mean(0)
        rc += np.sqrt(T) * (mb - mu).max() >= stat
        spa += max(0.0, np.max(np.sqrt(T) * (mb - mu_c) / sd)) >= spa_stat
    return {"rc_pvalue": rc / n_boot, "spa_pvalue": spa / n_boot, "best_idx": int(mu.argmax()), "K": K, "T": T}


def summary_tests(daily: pd.Series, n_trials: int = 1, seed: int = 0) -> dict:
    x = daily.to_numpy(float)
    lo, hi, p_le0 = bootstrap_ci(x, np.mean, seed=seed)
    slo, shi, _ = bootstrap_ci(x, sharpe, n_boot=1000, seed=seed)
    t, p = newey_west_t(x)
    return {
        "mean_daily": float(x.mean()), "mean_ci95": (lo, hi), "boot_p_mean_le0": p_le0,
        "sharpe_ci95": (slo, shi), "nw_t": t, "nw_p_one_sided": p,
        "psr_vs0": probabilistic_sharpe(x), "dsr": deflated_sharpe(x, n_trials),
    }
