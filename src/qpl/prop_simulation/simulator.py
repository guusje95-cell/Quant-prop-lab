"""Configurable prop-firm evaluation simulator + Monte Carlo.

Input is a sequence of trading days, each with:
  pnl   : realized day P&L (USD, after costs)
  worst : lowest intraday equity relative to the day's starting balance (<= 0),
          including open-trade adverse excursion (MAE) -> models real-time
          max-loss monitoring on unrealized P&L.

Rules modelled:
  * MLL: STATIC, EOD_TRAILING (floor = max EOD balance - MLL, optionally locked at
    the starting balance), checked intraday against `worst`.
  * DLL: either 'pause' (Topstep: positions liquidated, day P&L = -DLL, not a fail)
    or 'fail' (FTMO-style daily loss = evaluation failure).
  * Profit target, checked at end of day.
  * Consistency (Topstep-style): pass requires best_day <= c * total_profit, i.e. the
    effective target becomes max(target, best_day / c).  (FTMO 1-step 'Best Day' rule
    is the same algebra over positive days' profit.)
  * Minimum / maximum trading days (a 'trading day' = a day with >= 1 trade).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numba import njit

STATIC, EOD_TRAILING = 0, 1
PASS, FAIL_MLL, FAIL_DLL, TIMEOUT = 1, -1, -2, 0


@dataclass
class Rules:
    name: str
    start: float
    target: float
    mll: float
    mll_type: int = EOD_TRAILING
    lock_at_start: bool = True
    dll: float = np.nan
    dll_fail: bool = False
    consistency: float = np.nan
    min_days: int = 0
    max_days: int = 100000
    phases: list = field(default_factory=list)   # list of (target, min_days) for multi-phase (FTMO)
    monthly_fee: float = 0.0
    reset_fee: float = 0.0
    one_time_fee: float = 0.0
    activation_fee: float = 0.0


def topstep_50k(dll: bool = False) -> Rules:
    return Rules("Topstep 50K Combine" + (" +DLL" if dll else ""), 50_000, 3_000, 2_000, EOD_TRAILING, True,
                 dll=1_000.0 if dll else np.nan, dll_fail=False, consistency=0.55, min_days=2,
                 monthly_fee=49.0, reset_fee=49.0, activation_fee=149.0)


def topstep_100k() -> Rules:
    return Rules("Topstep 100K Combine", 100_000, 6_000, 3_000, EOD_TRAILING, True, consistency=0.55,
                 min_days=2, monthly_fee=99.0, reset_fee=99.0, activation_fee=149.0)


def topstep_150k() -> Rules:
    return Rules("Topstep 150K Combine", 150_000, 9_000, 4_500, EOD_TRAILING, True, consistency=0.55,
                 min_days=2, monthly_fee=199.0, reset_fee=199.0, activation_fee=149.0)


def mffu_50k_core() -> Rules:
    return Rules("MyFundedFutures 50K Core", 50_000, 3_000, 2_000, EOD_TRAILING, True, consistency=0.50,
                 min_days=2, monthly_fee=77.0, reset_fee=77.0)


def ftmo_2step_100k() -> Rules:
    return Rules("FTMO 2-Step 100K", 100_000, 10_000, 10_000, STATIC, False, dll=5_000.0, dll_fail=True,
                 min_days=4, phases=[(10_000.0, 4), (5_000.0, 4)], one_time_fee=590.0)


@njit(cache=True)
def run_eval(pnl, worst, ntr, start, target, mll, mll_type, lock, dll, dll_fail, cons, min_days, max_days):
    """Run one evaluation over the given day sequence.
    Returns (outcome, days_elapsed, trading_days, final_profit)."""
    bal = start
    hi_eod = start
    floor = start - mll
    best = 0.0
    tdays = 0
    n = len(pnl)
    for i in range(n):
        if i >= max_days:
            return TIMEOUT, i, tdays, bal - start
        p = pnl[i]
        w = worst[i]
        if ntr[i] > 0:
            tdays += 1
        # daily loss limit
        if not np.isnan(dll) and w <= -dll:
            if dll_fail:
                return FAIL_DLL, i + 1, tdays, bal - start - dll
            p = -dll
            w = -dll
        # intraday max-loss check (real-time, includes open P&L)
        if bal + w <= floor:
            return FAIL_MLL, i + 1, tdays, floor - start
        bal += p
        if bal <= floor:
            return FAIL_MLL, i + 1, tdays, floor - start
        if p > best:
            best = p
        prof = bal - start
        need = target
        if not np.isnan(cons) and cons > 0:
            need = max(target, best / cons)
        if prof >= need and tdays >= min_days:
            return PASS, i + 1, tdays, prof
        # end-of-day trailing update
        if mll_type == EOD_TRAILING and bal > hi_eod:
            hi_eod = bal
            nf = hi_eod - mll
            if lock and nf > start:
                nf = start
            if nf > floor:
                floor = nf
    return TIMEOUT, n, tdays, bal - start


@njit(cache=True)
def _block_bootstrap_idx(n_src, n_out, block, rng_seed):
    np.random.seed(rng_seed)
    out = np.empty(n_out, np.int64)
    k = 0
    while k < n_out:
        s = np.random.randint(0, n_src)
        L = np.random.geometric(1.0 / block) if block > 1 else 1
        for j in range(L):
            if k >= n_out:
                break
            out[k] = (s + j) % n_src
            k += 1
    return out


@njit(cache=True)
def _mc(pnl, worst, ntr, n_sims, horizon, block, seed, start, target, mll, mll_type, lock, dll, dll_fail,
        cons, min_days, max_days, pnl_scale, extra_cost_per_trade):
    res = np.empty((n_sims, 4))
    for s in range(n_sims):
        idx = _block_bootstrap_idx(len(pnl), horizon, block, seed + s)
        p = pnl[idx] * pnl_scale - extra_cost_per_trade * ntr[idx]
        w = worst[idx] * pnl_scale - extra_cost_per_trade * ntr[idx]
        o, d, td, fp = run_eval(p, w, ntr[idx], start, target, mll, mll_type, lock, dll, dll_fail, cons,
                                min_days, max_days)
        res[s, 0] = o; res[s, 1] = d; res[s, 2] = td; res[s, 3] = fp
    return res


def _phases(r: Rules):
    return r.phases if r.phases else [(r.target, r.min_days)]


def monte_carlo(daily, rules: Rules, n_sims: int = 5000, horizon: int = 750, block: int = 5, seed: int = 7,
                pnl_scale: float = 1.0, extra_cost_per_trade: float = 0.0) -> dict:
    """Block-bootstrap Monte Carlo of evaluation attempts.
    `daily` is a DataFrame with columns pnl, worst, ntrades (all trading days, incl. zero days)."""
    pnl = daily["pnl"].to_numpy(np.float64)
    worst = daily["worst"].to_numpy(np.float64)
    ntr = daily["ntrades"].to_numpy(np.int64)
    out_codes = np.zeros(n_sims)
    days = np.zeros(n_sims)
    seed_off = 0
    alive = np.ones(n_sims, bool)
    for ph_i, (tgt, mind) in enumerate(_phases(rules)):
        res = _mc(pnl, worst, ntr, n_sims, horizon, block, seed + seed_off, rules.start, tgt, rules.mll,
                  rules.mll_type, rules.lock_at_start, rules.dll, rules.dll_fail, rules.consistency, mind,
                  rules.max_days, pnl_scale, extra_cost_per_trade)
        seed_off += 1_000_003
        code = res[:, 0]
        days = days + np.where(alive, res[:, 1], 0)
        newly = alive & (code != PASS)
        out_codes[newly] = code[newly]
        alive = alive & (code == PASS)
    out_codes[alive] = PASS
    return summarize_mc(out_codes, days, rules)


def summarize_mc(codes: np.ndarray, days: np.ndarray, rules: Rules) -> dict:
    p_pass = float(np.mean(codes == PASS))
    p_mll = float(np.mean(codes == FAIL_MLL))
    p_dll = float(np.mean(codes == FAIL_DLL))
    p_to = float(np.mean(codes == TIMEOUT))
    dp = days[codes == PASS]
    df = days[(codes == FAIL_MLL) | (codes == FAIL_DLL)]
    q = lambda a, x: float(np.percentile(a, x)) if len(a) else np.nan
    res = {
        "rules": rules.name, "p_pass": p_pass, "p_fail": p_mll + p_dll, "p_fail_mll": p_mll, "p_fail_dll": p_dll,
        "p_timeout": p_to,
        "days_to_pass_mean": float(dp.mean()) if len(dp) else np.nan,
        "days_to_pass_p5": q(dp, 5), "days_to_pass_p25": q(dp, 25), "days_to_pass_p50": q(dp, 50),
        "days_to_pass_p75": q(dp, 75), "days_to_pass_p95": q(dp, 95),
        "days_to_fail_p50": q(df, 50), "days_to_fail_mean": float(df.mean()) if len(df) else np.nan,
    }
    # Expected attempts until first pass (geometric, ignoring timeouts) and expected cost.
    if p_pass > 0:
        exp_attempts = 1.0 / p_pass
        avg_days_per_attempt = float(np.mean(days))
        months = exp_attempts * avg_days_per_attempt / 21.0
        cost = (rules.monthly_fee * months + rules.reset_fee * (exp_attempts - 1) + rules.one_time_fee * exp_attempts
                + rules.activation_fee)
        res.update({"expected_attempts": exp_attempts, "expected_failed_evals": exp_attempts - 1,
                    "expected_cost_to_pass_usd": cost, "expected_trading_days_to_pass_incl_resets":
                    exp_attempts * avg_days_per_attempt})
    return res


def historical_starts(daily, rules: Rules, step: int = 1, max_days: int = 750) -> dict:
    """Start an evaluation on every `step`-th historical day and run on the real path."""
    pnl = daily["pnl"].to_numpy(np.float64)
    worst = daily["worst"].to_numpy(np.float64)
    ntr = daily["ntrades"].to_numpy(np.int64)
    codes, days = [], []
    for s in range(0, len(pnl), step):
        code_tot, d_tot, ok = PASS, 0, True
        off = s
        for tgt, mind in _phases(rules):
            sl = slice(off, min(off + max_days, len(pnl)))
            o, d, td, fp = run_eval(pnl[sl], worst[sl], ntr[sl], rules.start, tgt, rules.mll, rules.mll_type,
                                    rules.lock_at_start, rules.dll, rules.dll_fail, rules.consistency, mind,
                                    rules.max_days)
            d_tot += d
            off += d
            if o != PASS:
                code_tot = o
                break
        if code_tot == TIMEOUT:
            continue  # ran out of history: unresolved, excluded
        codes.append(code_tot)
        days.append(d_tot)
    return summarize_mc(np.array(codes, float), np.array(days, float), rules) | {"n_starts": len(codes)}
