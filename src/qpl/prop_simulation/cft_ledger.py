"""Day-by-day cash ledger for the CFT two-speed pipeline (gen34 policy) with a challenge BUDGET.

Policy: buy a challenge (pay fee) -> trade the challenge series until pass / fail -> on fail buy the next one (while budget
lasts) -> on pass trade the funded series, withdraw split*(1-proc)*profit every 30 days (equity reset to start), and after
a funded breach go back to buying challenges (while budget lasts). Daily-loss and max-loss rules as in cft_daily.

All amounts in USD for an account of size `account`. Wealth = cumulative payouts - cumulative fees (cash in your pocket)."""
from __future__ import annotations

import numpy as np

from qpl.prop_simulation.cft_daily import PASS, PROGRAMS, _run


def run_ledger(rc, loc, hic, rf, lof, hif, s, program="1PHASE", account=100_000.0, fee=798.0, budget=5,
               horizon=730, split=0.8, proc=0.05):
    P = PROGRAMS[program]; mx, daily, trailing = P["max"], P["daily"], P["trailing"]
    end = min(len(rc), s + horizon)
    cash = np.zeros(end - s)                                  # cash flow per day
    t = s; bought = passed = breaches = payouts_n = 0; first_pass_day = first_payout_day = None
    while t < end:
        if bought >= budget:
            break
        cash[t - s] -= fee; bought += 1; ok = True
        for tgt in P["targets"]:
            code, d = _run(rc, t, tgt, daily, mx, trailing, 1.5, "optimistic", end - t, lo=loc, hi=hic)
            t += d
            if code != PASS:
                ok = False; break
        if not ok:
            continue
        passed += 1
        if first_pass_day is None:
            first_pass_day = t - s
        E = 1.0; peak = 1.0; alive = True
        while t < end and alive:
            stop = min(t + 30, end)
            for j in range(t, stop):
                x = rf[j] if np.isfinite(rf[j]) else 0.0
                low = E * (1 + lof[j])
                if trailing:
                    peak = max(peak, E * (1 + hif[j]))
                floor = min(peak - mx, 1.0) if trailing else 1.0 - mx
                if low < E - daily or low < floor:
                    alive = False; breaches += 1; t = j + 1; break
                E *= 1 + x; peak = max(peak, E)
            if alive:
                t = stop
                if E > 1.0:
                    pay = split * (1 - proc) * (E - 1.0) * account
                    cash[min(t, end) - s - 1] += pay; payouts_n += 1
                    if first_payout_day is None:
                        first_payout_day = t - s
                    E = 1.0; peak = 1.0
    wealth = np.cumsum(cash)
    return {"wealth": wealth, "bought": bought, "passed": passed, "funded_breaches": breaches, "payouts": payouts_n,
            "fees": bought * fee, "paid": float(cash[cash > 0].sum()), "net": float(wealth[-1]) if len(wealth) else 0.0,
            "first_pass_day": first_pass_day, "first_payout_day": first_payout_day}
