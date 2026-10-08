"""Robustness / falsification suite applied to a frozen candidate specification."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from ..backtesting import accounting as A
from ..instruments import Instrument
from ..research import pipeline as P
from ..statistics import metrics as M
from ..statistics import tests as T


def cost_stress(tr: pd.DataFrame, inst: Instrument, days, period, contracts=1) -> pd.DataFrame:
    rows = []
    for label, cm, sm, norm in [("baseline", 1, 1, True), ("cost1.5x", 1.5, 1.5, True), ("cost2x", 2, 2, True),
                                ("cost3x", 3, 3, True), ("slip2x_only", 1, 2, True), ("slip4x_only", 1, 4, True),
                                ("historical_price_ticks", 1, 1, False), ("hist_price_2x", 2, 2, False),
                                ("frictionless", 0, 0, True)]:
        u = P.usd(tr, inst, contracts=contracts, cost_mult=cm, slip_mult=sm, norm=norm)
        m = P.split_metrics(u, days, {"p": period})["p"]
        rows.append({"scenario": label, "sharpe": m["sharpe"], "total_usd": m["total_usd"],
                     "expectancy": m.get("expectancy_usd"), "pf": m.get("profit_factor"), "max_dd": m["max_dd_usd"]})
    return pd.DataFrame(rows)


def neighbors(strategy: str, ctx, base: dict, grid: dict, inst: Instrument, days, period) -> pd.DataFrame:
    keys = list(grid)
    rows = []
    for vals in itertools.product(*grid.values()):
        prm = dict(base, **dict(zip(keys, vals)))
        tr = P.backtest(strategy, ctx, prm, inst)
        u = P.usd(tr, inst, contracts=1)
        m = P.split_metrics(u, days, {"p": period})["p"]
        rows.append({**dict(zip(keys, vals)), "sharpe": m["sharpe"], "total": m["total_usd"],
                     "trades": m.get("trades", 0), "max_dd": m["max_dd_usd"]})
    return pd.DataFrame(rows)


def regimes(daily: pd.Series, price_close: pd.Series) -> dict:
    """Bull/bear (close vs 200d SMA, known at prior close), vol terciles (20d realized, prior day),
    yearly, and named crisis windows."""
    pc = price_close.reindex(daily.index).ffill()
    sma = pc.rolling(200, min_periods=150).mean().shift(1)
    trend = np.where(pc.shift(1) > sma, "bull", "bear")
    rv = np.log(pc).diff().rolling(20).std().shift(1)
    q = rv.quantile([1 / 3, 2 / 3]).to_numpy()
    vol = np.where(rv <= q[0], "low_vol", np.where(rv <= q[1], "mid_vol", "high_vol"))
    out = {}
    df = pd.DataFrame({"pnl": daily, "trend": trend, "vol": vol})
    for col in ("trend", "vol"):
        g = df.groupby(col)["pnl"]
        out[col] = {k: {"days": int(len(v)), "mean": float(v.mean()), "sharpe": float(v.mean() / v.std() * np.sqrt(252))
                        if v.std() > 0 else np.nan, "total": float(v.sum())} for k, v in g}
    yr = df.groupby(df.index.year)["pnl"]
    out["yearly"] = {int(k): {"total": float(v.sum()), "sharpe": float(v.mean() / v.std() * np.sqrt(252)) if v.std() > 0 else np.nan}
                     for k, v in yr}
    crises = {"2015-08_china_deval": ("2015-08-10", "2015-09-30"), "2018-02_volmageddon": ("2018-01-26", "2018-03-31"),
              "2018-Q4_selloff": ("2018-10-01", "2018-12-31"), "2020_covid_crash": ("2020-02-19", "2020-04-30"),
              "2022_bear_market": ("2022-01-03", "2022-10-14"), "2023-03_bank_crisis": ("2023-03-06", "2023-03-31")}
    out["crises"] = {k: float(daily.loc[a:b].sum()) for k, (a, b) in crises.items() if len(daily.loc[a:b])}
    return out


def walk_forward(strategy: str, ctx, grid: list[dict], inst: Instrument, days, start: str, end: str,
                 train_years: int = 3, test_years: int = 1) -> dict:
    """Rolling re-selection: on each in-sample window pick the variant with the best Sharpe,
    apply it to the next out-of-sample year. Returns stitched OOS daily P&L + selections."""
    dl = {}
    for i, prm in enumerate(grid):
        tr = P.backtest(strategy, ctx, prm, inst)
        u = P.usd(tr, inst, contracts=1)
        dl[i] = A.daily_pnl(u, days)["pnl"]
    D = pd.DataFrame(dl)
    D = D.loc[start:end]
    years = sorted(set(D.index.year))
    oos, picks = [], []
    for k in range(train_years, len(years), test_years):
        ins = D[(D.index.year >= years[k - train_years]) & (D.index.year < years[k])]
        out = D[(D.index.year >= years[k]) & (D.index.year < years[k] + test_years)]
        if len(out) == 0:
            continue
        sh = ins.mean() / ins.std()
        best = int(sh.idxmax())
        oos.append(out[best])
        picks.append({"test_year": years[k], "pick": grid[best], "is_sharpe": float(sh.max() * np.sqrt(252)),
                      "oos_sharpe": float(out[best].mean() / out[best].std() * np.sqrt(252)) if out[best].std() > 0 else np.nan,
                      "median_variant_oos_sharpe": float((out.mean() / out.std()).median() * np.sqrt(252))})
    s = pd.concat(oos) if oos else pd.Series(dtype=float)
    return {"oos_daily": s, "picks": picks,
            "oos_sharpe": float(s.mean() / s.std() * np.sqrt(252)) if len(s) else np.nan,
            "is_mean_sharpe": float(np.mean([p["is_sharpe"] for p in picks])) if picks else np.nan,
            "wf_efficiency": (float(s.mean() / s.std() * np.sqrt(252)) / float(np.mean([p["is_sharpe"] for p in picks])))
            if picks else np.nan,
            "pct_oos_years_positive": float(np.mean([p["oos_sharpe"] > 0 for p in picks])) if picks else np.nan,
            "all_variants_daily": D}


def mc_paths(daily: np.ndarray, n: int = 5000, horizon: int | None = None, block: float = 5.0, seed: int = 11) -> dict:
    """Stationary-block-bootstrap equity paths: distribution of return, Sharpe, max DD, longest
    losing-day streak, recovery time."""
    rng = np.random.default_rng(seed)
    x = np.asarray(daily, float)
    H = horizon or len(x)
    idx = T.stationary_bootstrap_indices(len(x), n, block, rng)[:, :H]
    P_ = x[idx]
    eq = P_.cumsum(1)
    peak = np.maximum.accumulate(np.concatenate([np.zeros((n, 1)), eq], 1), 1)[:, 1:]
    dd = (eq - peak).min(1)
    sh = P_.mean(1) / P_.std(1) * np.sqrt(252)
    ls = []
    for row in P_[: min(n, 2000)]:
        ls.append(M.streaks(row[row != 0])[1])
    pct = lambda a: {f"p{q}": float(np.percentile(a, q)) for q in (5, 25, 50, 75, 95)}
    return {"total": pct(eq[:, -1]), "sharpe": pct(sh), "max_dd": pct(-dd), "loss_streak_days": pct(np.array(ls)),
            "p_total_le0": float(np.mean(eq[:, -1] <= 0))}


def trade_shuffle_dd(pnl: np.ndarray, n: int = 5000, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        e = np.cumsum(rng.permutation(pnl))
        out.append(-(e - np.maximum.accumulate(np.r_[0, e])[1:]).min())
    out = np.array(out)
    return {f"p{q}": float(np.percentile(out, q)) for q in (5, 25, 50, 75, 95)}


def stat_validation(daily: pd.Series, n_trials: int, family_matrix: pd.DataFrame | None = None) -> dict:
    res = T.summary_tests(daily, n_trials=n_trials)
    if family_matrix is not None and family_matrix.shape[1] > 1:
        res["reality_check"] = T.whites_reality_check(family_matrix.fillna(0).to_numpy(), n_boot=1000)
    return res
