"""FTMO 2-Step (Swing) simulation on DAILY strategy returns (config/prop_ftmo_trend_protocol.json; rules UNCERTAIN).

Each phase starts a fresh account at 1.0. Fail if equity < 0.90 (static max loss) or the daily-loss proxy triggers:
  intraday_low_t = E_{t-1} * (1 + k * min(r_t, 0))           (k = 1.5: close-to-close loss scaled for intraday excursions)
  fail if intraday_low_t < B_t - 0.05,  B_t = 'balance at midnight':
     optimistic   B_t = E_{t-1}                                (P&L realised daily)
     conservative B_t = max(E_{t-10..t-1})                     (floating losses of held positions accrue against the balance)
Daily returns are compounded on the phase account. Phase 1 target +10%, phase 2 +5%, min 4 trading days each.
Funded: monthly (21 trading days) withdraw split * profit above 1.0 and reset to 1.0; same loss rules."""
from __future__ import annotations

import numpy as np

PASS, FAIL_MAX, FAIL_DAILY, OPEN = 1, -1, -2, 0


def _phase(r: np.ndarray, s: int, target: float, k: float, mode: str, max_days: int, min_days: int = 4):
    E = 1.0; hist = [1.0]
    for j in range(s, min(len(r), s + max_days)):
        x = r[j]
        if not np.isfinite(x):
            x = 0.0
        B = E if mode == "optimistic" else max(hist[-10:])
        low = E * (1 + k * min(x, 0.0))
        if low < B - 0.05:
            return FAIL_DAILY, j - s + 1
        E *= 1 + x
        hist.append(E)
        if E < 0.90:
            return FAIL_MAX, j - s + 1
        if E >= 1 + target and (j - s + 1) >= min_days:
            return PASS, j - s + 1
    return OPEN, min(len(r) - s, max_days)


def _funded(r: np.ndarray, s: int, months: int, k: float, mode: str, split: float):
    E = 1.0; hist = [1.0]; paid = 0.0; first_payout = None
    for m in range(months):
        for j in range(s + 21 * m, s + 21 * (m + 1)):
            if j >= len(r):
                return paid, "data_end", first_payout
            x = r[j] if np.isfinite(r[j]) else 0.0
            B = E if mode == "optimistic" else max(hist[-10:])
            if E * (1 + k * min(x, 0.0)) < B - 0.05:
                return paid, "fail_daily", first_payout
            E *= 1 + x; hist.append(E)
            if E < 0.90:
                return paid, "fail_max", first_payout
        if E > 1.0:
            paid += split * (E - 1.0); E = 1.0; hist = [1.0]
            first_payout = first_payout or (m + 1)
    return paid, "survived", first_payout


def simulate_start(r: np.ndarray, s: int, k=1.5, mode="conservative", eval_max_days=756, funded_months=12, split=0.8):
    c1, d1 = _phase(r, s, 0.10, k, mode, eval_max_days)
    out = {"p1": c1, "d1": d1}
    if c1 != PASS:
        return out
    s2 = s + d1
    c2, d2 = _phase(r, s2, 0.05, k, mode, eval_max_days - d1)
    out.update({"p2": c2, "d2": d2})
    if c2 != PASS:
        return out
    paid, status, fp = _funded(r, s2 + d2, funded_months, k, mode, split)
    out.update({"payout_frac": paid, "funded_status": status, "first_payout_month": fp})
    return out


def summarize(results: list[dict], max_days_pass: int = 504) -> dict:
    n = len(results)
    p1 = np.array([x["p1"] for x in results])
    both = np.array([x.get("p2") == PASS for x in results])
    days = np.array([x["d1"] + x.get("d2", 0) for x in results])
    failed_eval = np.array([(x["p1"] < 0) or (x.get("p2", 0) < 0) for x in results])
    open_ = np.array([(x["p1"] == OPEN) or (x.get("p2") == OPEN) for x in results])
    daily_fail = np.array([(x["p1"] == FAIL_DAILY) or (x.get("p2") == FAIL_DAILY) for x in results])
    pay = np.array([x.get("payout_frac", 0.0) for x in results])
    fs = [x.get("funded_status") for x in results if x.get("p2") == PASS]
    return {"n_starts": n, "P_pass_phase1": float(np.mean(p1 == PASS)), "P_pass_both": float(both.mean()),
            "P_pass_both_within_24m": float(np.mean(both & (days <= max_days_pass))), "P_fail_eval": float(failed_eval.mean()),
            "P_fail_daily_rule": float(daily_fail.mean()), "P_unresolved_36m": float(open_.mean()),
            "median_days_to_pass_both": float(np.median(days[both])) if both.any() else None,
            "funded_survive_12m": float(np.mean([f == "survived" for f in fs])) if fs else None,
            "E_payout_frac_per_attempt_12m": float(pay.mean()),
            "E_payout_frac_given_funded": float(pay[both].mean()) if both.any() else None}
