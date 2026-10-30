"""Validation pipeline for a daily return series (and optionally a family of competing variants): chronological periods,
uncertainty (non-normal SE, stationary block bootstrap), selection adjustments (project haircut SR - E[max of N nulls], Deflated
Sharpe Ratio, Harvey-Liu Bonferroni / BHY haircuts), CSCV probability of backtest overfitting on a variant family, simple stress
tests, and acceptance criteria per use case (config/hub_acceptance.json). See research/v99/METHODOLOGY_AUDIT.md for what each
number does and does not mean: none of them is a forecast of live Sharpe."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

from qpl.hub.metrics import summary, to_daily

G = 0.5772156649
ROOT = Path(__file__).resolve().parents[3]


def emax_null(n_trials: int, T: int) -> float:
    """Expected maximum per-period Sharpe of n_trials independent zero-edge strategies over T periods (Bailey & Lopez de Prado)."""
    if n_trials <= 1:
        return 0.0
    return np.sqrt(1.0 / T) * ((1 - G) * norm.ppf(1 - 1 / n_trials) + G * norm.ppf(1 - 1 / (n_trials * np.e)))


def selection_adjusted(d: pd.Series, n_trials: int, ppy: int = 365) -> dict:
    d = to_daily(d).dropna(); T = len(d); sr = d.mean() / d.std(ddof=1); g3, g4 = skew(d), kurtosis(d, fisher=False)
    se = np.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (T - 1))
    e = emax_null(n_trials, T); yrs = T / ppy; t = sr * np.sqrt(ppy) * np.sqrt(yrs); p = 2 * norm.sf(t)
    hl = {}
    for nm, padj in (("bonferroni", min(1, n_trials * p)), ("bhy", min(1, n_trials * sum(1 / i for i in range(1, n_trials + 1)) * p))):
        hl[nm] = float((norm.isf(padj / 2) if padj < 1 else 0.0) / np.sqrt(yrs))
    return {"n_trials": n_trials, "days": T, "sharpe": float(sr * np.sqrt(ppy)), "se_annual": float(se * np.sqrt(ppy)),
            "project_haircut_sharpe": float((sr - e) * np.sqrt(ppy)), "expected_max_null_sharpe": float(e * np.sqrt(ppy)),
            "dsr": float(norm.cdf((sr - e) / se)), "harvey_liu_bonferroni": hl["bonferroni"], "harvey_liu_bhy": hl["bhy"], "t_stat": float(t)}


def block_bootstrap_sharpe(d: pd.Series, B: int = 2000, block: int = 20, seed: int = 7, ppy: int = 365) -> dict:
    x = to_daily(d).dropna().to_numpy(); n = len(x); rng = np.random.default_rng(seed); out = np.empty(B)
    for b in range(B):
        idx = np.empty(n, dtype=int); k = 0
        while k < n:
            s = rng.integers(0, n); L = rng.geometric(1 / block); m = min(L, n - k)
            idx[k:k + m] = (s + np.arange(m)) % n; k += m
        y = x[idx]; out[b] = y.mean() / y.std(ddof=1) * np.sqrt(ppy)
    return {"p5": float(np.percentile(out, 5)), "p50": float(np.percentile(out, 50)), "p95": float(np.percentile(out, 95)),
            "p_le_0": float((out <= 0).mean()), "B": B, "block": block, "seed": seed}


def pbo_cscv(family: pd.DataFrame, S: int = 16, max_splits: int = 2000, seed: int = 7, ppy: int = 365) -> dict:
    """Probability of backtest overfitting (Bailey et al. 2017) for a DAILY return matrix (columns = competing variants)."""
    M = family.dropna(how="all").fillna(0.0).to_numpy(); T, nb = M.shape
    if nb < 2 or T < S * 10:
        return {"status": "insufficient data", "variants": nb, "days": T}
    rng = np.random.default_rng(seed); blocks = np.array_split(np.arange(T), S); combos = list(itertools.combinations(range(S), S // 2))
    pick = [combos[i] for i in rng.choice(len(combos), size=min(max_splits, len(combos)), replace=False)]
    srf = lambda X: X.mean(0) / np.where(X.std(0, ddof=1) > 0, X.std(0, ddof=1), np.nan) * np.sqrt(ppy)
    logits, is_b, oos_b = [], [], []
    for cmb in pick:
        tr = np.concatenate([blocks[i] for i in cmb]); te = np.concatenate([blocks[i] for i in range(S) if i not in cmb])
        a, b = srf(M[tr]), srf(M[te]); j = int(np.nanargmax(a)); rk = np.nansum(b < b[j]) + 0.5 * (np.nansum(b == b[j]) - 1)
        w = (rk + 1) / (nb + 1); logits.append(np.log(w / (1 - w))); is_b.append(a[j]); oos_b.append(b[j])
    C = np.corrcoef(M.T); ev = np.linalg.eigvalsh(np.nan_to_num(C)); ev = ev[ev > 1e-12] / ev[ev > 1e-12].sum()
    return {"status": "ok", "pbo": float(np.mean(np.array(logits) <= 0)), "variants": nb, "splits": len(pick),
            "is_winner_sharpe": float(np.mean(is_b)), "oos_winner_sharpe": float(np.mean(oos_b)),
            "selection_decay": float(np.mean(is_b) - np.mean(oos_b)), "effective_independent_variants": float(np.exp(-(ev * np.log(ev)).sum()))}


def periods(d: pd.Series, splits: dict, ppy: int = 365) -> dict:
    d = to_daily(d)
    return {k: summary(d.loc[a:b], ppy) for k, (a, b) in splits.items()}


def stress(d: pd.Series, turnover_per_day: pd.Series | None = None, extra_cost_bps=(5, 10), delay_days: int = 1, ppy: int = 365) -> dict:
    """Cheap stress tests on a return series: extra cost on a known daily turnover, a one-day delay (shift), dropping the best 1% of
    days, and a 'strongest-year removed' check. Delay on a return series is only a proxy for execution delay (it moves every return)."""
    d = to_daily(d).dropna(); out = {"base": summary(d, ppy).get("sharpe")}
    if turnover_per_day is not None:
        t = to_daily(turnover_per_day).reindex(d.index).fillna(0.0)
        for bp in extra_cost_bps:
            out[f"extra_cost_{bp}bp"] = summary(d - t * bp / 1e4, ppy).get("sharpe")
    out["drop_best_1pct_days"] = summary(d[d < d.quantile(0.99)], ppy).get("sharpe")
    yr = d.groupby(d.index.year).sum(); best = int(yr.idxmax())
    out[f"without_best_year_{best}"] = summary(d[d.index.year != best], ppy).get("sharpe")
    out["shifted_one_period_proxy"] = summary(d.shift(delay_days).dropna(), ppy).get("sharpe")
    return out


def load_criteria(use_case: str) -> dict:
    return json.loads((ROOT / "config/hub_acceptance.json").read_text())[use_case]


def evaluate(d: pd.Series, n_trials: int, use_case: str, splits: dict | None = None, family: pd.DataFrame | None = None,
             ppy: int = 365) -> dict:
    """Run the pipeline and apply the use case's criteria. Returns every number plus a verdict: 'pass', 'fail' or 'insufficient evidence'."""
    crit = load_criteria(use_case); d = to_daily(d).dropna()
    splits = splits or {"development": ("2022-01-01", "2022-12-31"), "validation": ("2023-01-01", "2024-12-31"), "holdout": ("2025-01-01", "2099-12-31")}
    rep = {"use_case": use_case, "criteria": crit, "summary": summary(d, ppy), "periods": {k: v.get("sharpe") for k, v in periods(d, splits, ppy).items()},
           "selection": selection_adjusted(d, n_trials, ppy), "bootstrap": block_bootstrap_sharpe(d, ppy=ppy), "stress": stress(d, ppy=ppy)}
    if family is not None:
        rep["pbo"] = pbo_cscv(family, ppy=ppy)
    reasons, insufficient = [], []
    if rep["summary"].get("days", 0) < crit["min_days"]:
        insufficient.append(f"only {rep['summary'].get('days', 0)} days (< {crit['min_days']})")
    for k, v in rep["periods"].items():
        if v is None:
            insufficient.append(f"no data in {k}")
        elif v < crit["min_period_sharpe"]:
            reasons.append(f"{k} Sharpe {v:.2f} < {crit['min_period_sharpe']}")
    if rep["selection"]["project_haircut_sharpe"] < crit["min_selection_adjusted_sharpe"]:
        reasons.append(f"selection-adjusted Sharpe {rep['selection']['project_haircut_sharpe']:.2f} < {crit['min_selection_adjusted_sharpe']}")
    if rep["bootstrap"]["p5"] < crit["min_bootstrap_p5_sharpe"]:
        reasons.append(f"bootstrap 5% Sharpe {rep['bootstrap']['p5']:.2f} < {crit['min_bootstrap_p5_sharpe']}")
    if rep["summary"].get("max_drawdown", 0) < -crit["max_drawdown"]:
        reasons.append(f"max drawdown {rep['summary']['max_drawdown']:.1%} beyond {crit['max_drawdown']:.0%}")
    if family is not None and rep["pbo"].get("status") == "ok" and rep["pbo"]["pbo"] > crit["max_pbo"]:
        reasons.append(f"PBO {rep['pbo']['pbo']:.2f} > {crit['max_pbo']}")
    rep["verdict"] = "insufficient evidence" if insufficient else ("fail" if reasons else "pass")
    rep["reasons"] = insufficient + reasons
    return rep
