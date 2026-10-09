"""Path-dependent prop-evaluation simulation with trade-level sizing policies.

Input: a per-day list of trades for ONE contract unit (pnl_usd, mae_usd, risk_ref_usd). A policy
maps the account state (balance, floor, day P&L, trade stats) to an integer number of contracts
before each trade. Rules: Topstep-style EOD-trailing max loss (checked against MAE intraday),
optional daily loss pause, consistency target, minimum days.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class State:
    balance: float
    floor: float
    start: float
    day_pnl: float = 0.0
    eod_high: float = 0.0


def fixed(n=1):
    def pol(st, tr):
        return n
    return pol


def drawdown_aware(n_full=2, n_reduced=1, cushion_frac=0.5, mll=2000.0):
    """Full size while the cushion above the floor exceeds cushion_frac*MLL, else reduced."""
    def pol(st, tr):
        return n_full if (st.balance - st.floor) > cushion_frac * mll else n_reduced
    return pol


def daily_stop(base_pol, stop_usd=300.0):
    """No new trades once the day's realized P&L <= -stop_usd."""
    def pol(st, tr):
        return 0 if st.day_pnl <= -stop_usd else base_pol(st, tr)
    return pol


def kelly_uncertainty(mu_lo: float, var: float, frac=0.25, cap=5):
    """Fractional Kelly using a LOWER confidence bound of per-trade expectancy (per contract).
    If the lower bound <= 0 the policy does not trade."""
    def pol(st, tr):
        if mu_lo <= 0:
            return 0
        f = frac * mu_lo / var                       # fraction of capital at risk per $1 of P&L variance
        cushion = st.balance - st.floor               # risk capital = distance to the max-loss floor
        return int(max(0, min(cap, math.floor(f * cushion))))
    return pol


def run(days_trades, pol, start=50_000.0, target=3_000.0, mll=2_000.0, lock=True, consistency=0.55,
        min_days=2, dll=None, max_days=100_000):
    st = State(start, start - mll, start, eod_high=start)
    best = 0.0
    tdays = 0
    for i, trades in enumerate(days_trades):
        if i >= max_days:
            return 0, i
        st.day_pnl = 0.0
        traded = False
        for (pnl, mae) in trades:
            q = pol(st, (pnl, mae))
            if q <= 0:
                continue
            traded = True
            if st.balance + st.day_pnl + q * mae <= st.floor:          # intraday breach (MAE incl. costs)
                return -1, i + 1
            st.day_pnl += q * pnl
            if dll is not None and st.day_pnl <= -dll:
                break
        tdays += traded
        st.balance += st.day_pnl
        if st.balance <= st.floor:
            return -1, i + 1
        best = max(best, st.day_pnl)
        prof = st.balance - start
        if prof >= max(target, best / consistency if consistency else 0) and tdays >= min_days:
            return 1, i + 1
        if st.balance > st.eod_high:
            st.eod_high = st.balance
            nf = st.eod_high - mll
            if lock:
                nf = min(nf, start)
            st.floor = max(st.floor, nf)
    return 0, len(days_trades)


def monte_carlo(days_trades, pol_factory, n=3000, horizon=750, block=5, seed=1, **rules):
    rng = np.random.default_rng(seed)
    N = len(days_trades)
    codes, durs = [], []
    for _ in range(n):
        seq = []
        while len(seq) < horizon:
            s = int(rng.integers(0, N))
            L = int(rng.geometric(1 / block))
            seq.extend(days_trades[(s + j) % N] for j in range(L))
        c, d = run(seq[:horizon], pol_factory(), **rules)
        codes.append(c); durs.append(d)
    codes, durs = np.array(codes), np.array(durs)
    dp = durs[codes == 1]
    return {"p_pass": float(np.mean(codes == 1)), "p_fail": float(np.mean(codes == -1)), "p_unresolved": float(np.mean(codes == 0)),
            "days_to_pass_p50": float(np.median(dp)) if len(dp) else None,
            "days_to_pass_p90": float(np.percentile(dp, 90)) if len(dp) else None}
