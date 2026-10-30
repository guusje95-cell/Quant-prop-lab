"""Income scenario engine for the business goal (e.g. EUR 10,000 a month). It answers "what would have to be true", not "what will
happen". Monthly cash is simulated account by account with the firm rule engine (challenge fees, failures, funded breaches,
payout cadence and split) on block-bootstrapped book returns shifted to an ASSUMED live Sharpe; then payout rejection, payout
delay, operating costs, FX and a flat tax reserve are applied. Accounts on the same strategy share the same return path (they pass
and fail together). Sharpe is never converted directly into income."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

import numpy as np
import pandas as pd

from qpl.hub.db import now, tx
from qpl.hub.prop import daily_with_stop, shift_to_sharpe
from qpl.lab import propfirms as PF

SCENARIOS = {  # every number is an assumption the user can change
    "conservative": {"live_sharpe": 1.0, "payout_reject_prob": 0.10, "payout_delay_days": 14, "monthly_costs_usd": 150.0},
    "base": {"live_sharpe": 1.5, "payout_reject_prob": 0.05, "payout_delay_days": 7, "monthly_costs_usd": 100.0},
    "optimistic": {"live_sharpe": 2.0, "payout_reject_prob": 0.02, "payout_delay_days": 5, "monthly_costs_usd": 100.0},
}
DEFAULT_PLAN = [  # (preset, start offset days, challenge budget)
    {"preset": "HyroTrader Two-Step $200k", "start_day": 0, "budget": 3},
    {"preset": "HyroTrader Two-Step $200k", "start_day": 180, "budget": 3},
]


def simulate(hourly_unit: pd.Series, scenario: dict, plan: list[dict] = None, target_month_eur: float = 10_000.0, usd_per_eur: float = 1.08,
             tax_rate: float = 0.37, horizon_days: int = 730, n_paths: int = 400, risk: float = 1.5, stop_frac: float = 0.5,
             window=("2022-01-01", "2026-09-30 23:00"), seed: int = 5) -> dict:
    plan = plan or DEFAULT_PLAN; rng = np.random.default_rng(seed)
    h = shift_to_sharpe(hourly_unit, scenario["live_sharpe"]).loc[window[0]:window[1]]
    months = horizon_days // 30; Mo = np.zeros((n_paths, months))
    firms = [PF.PRESETS[p["preset"]] for p in plan]
    days_cache = {}
    for i, f in enumerate(firms):
        key = (f.daily_loss, risk)
        if key not in days_cache:
            days_cache[key] = daily_with_stop(h * risk, stop_frac * f.daily_loss)
    base_days = next(iter(days_cache.values()))
    n = len(base_days); block = 20; first_pay = []
    for k in range(n_paths):
        idx = np.empty(horizon_days + max(p["start_day"] for p in plan) + 1, dtype=int); j = 0     # one shared bootstrap path for all accounts
        while j < len(idx):
            s = rng.integers(0, n - block); idx[j:j + block] = np.arange(s, s + block)[: len(idx) - j]; j += block
        cash = np.zeros(horizon_days)
        for p, f in zip(plan, firms):
            D = days_cache[(f.daily_loss, risk)]; r, lo, hi = D["net"].to_numpy(), D["worst"].to_numpy(), D["best"].to_numpy()
            x = idx[: horizon_days - p["start_day"]] if p["start_day"] < horizon_days else idx[:0]
            if len(x) == 0:
                continue
            cal = np.arange(len(x))
            L = PF._ledger(r[x], lo[x], hi[x], r[x], lo[x], hi[x], cal, 0, len(x), f, p["budget"])
            flows = np.diff(np.concatenate([[0.0], L["wealth"]]))
            pos = np.where(flows > 0)[0]
            for t in pos:                                          # payout rejection and delay
                amt = flows[t]; flows[t] = 0.0
                if rng.random() >= scenario["payout_reject_prob"]:
                    tt = t + scenario["payout_delay_days"]
                    if tt < len(flows):
                        flows[tt] += amt
            cash[p["start_day"]: p["start_day"] + len(flows)] += flows
        cash -= scenario["monthly_costs_usd"] / 30.0
        m = cash[: months * 30].reshape(months, 30).sum(axis=1) / usd_per_eur
        Mo[k] = m
        fp = np.argmax(np.cumsum(cash > 0) > 0) if (cash > 0).any() else np.nan; first_pay.append(fp)
    yearly = Mo.reshape(n_paths, -1, 12).sum(axis=2) if months % 12 == 0 else Mo.sum(axis=1, keepdims=True)
    after_tax = np.where(yearly > 0, yearly * (1 - tax_rate), yearly)
    second_year = Mo[:, 12:24] if months >= 24 else Mo
    hit = second_year >= target_month_eur
    streak3 = np.mean([any(row[i:i + 3].all() for i in range(len(row) - 2)) for row in hit]) if hit.shape[1] >= 3 else float("nan")
    cum = Mo.cumsum(axis=1)
    return {"scenario": scenario, "plan": plan, "assumptions": {"usd_per_eur": usd_per_eur, "tax_rate_flat_on_positive_years": tax_rate, "risk": risk,
            "daily_stop_frac_of_limit": stop_frac, "return_window": list(window), "bootstrap_block_days": 20, "paths": n_paths, "seed": seed},
            "monthly_net_cash_eur_before_tax": {"mean": float(Mo.mean()), "p10": float(np.percentile(Mo, 10)), "p50": float(np.percentile(Mo, 50)), "p90": float(np.percentile(Mo, 90))},
            "second_year_mean_month_eur": float(second_year.mean()),
            "P_month_at_or_above_target_in_year2": float(hit.mean()), "P_three_consecutive_target_months_in_year2": float(streak3),
            "P_net_loss_over_horizon": float((cum[:, -1] < 0).mean()), "horizon_net_eur_p10_p50_p90": [float(np.percentile(cum[:, -1], q)) for q in (10, 50, 90)],
            "annual_after_tax_eur_mean": [float(x) for x in after_tax.mean(axis=0)],
            "worst_cumulative_cash_eur_p10": float(np.percentile(cum.min(axis=1), 10)),
            "median_days_to_first_cash": float(np.nanmedian(first_pay)) if np.isfinite(first_pay).any() else None,
            "target_month_eur": target_month_eur,
            "caveat": "model estimate conditional on the assumed live Sharpe and firm rules (project presets, mostly unverified); accounts on one strategy move together; tax is a flat placeholder, not advice"}


def required_accounts(hourly_unit: pd.Series, scenario: dict, target_month_eur: float = 10_000.0, preset: str = "HyroTrader Two-Step $200k",
                      max_accounts: int = 12, **kw) -> dict:
    """Smallest number of identical staggered accounts (one every 90 days) whose year-2 mean month reaches the target (model)."""
    rows = []
    for k in range(1, max_accounts + 1):
        plan = [{"preset": preset, "start_day": 90 * i, "budget": 3} for i in range(k)]
        r = simulate(hourly_unit, scenario, plan, target_month_eur, horizon_days=730 + 90 * 0, **kw)
        rows.append({"accounts": k, "year2_mean_month_eur": r["second_year_mean_month_eur"], "P_month_ge_target": r["P_month_at_or_above_target_in_year2"],
                     "P_net_loss": r["P_net_loss_over_horizon"]})
        if r["second_year_mean_month_eur"] >= target_month_eur:
            break
    return {"rows": rows, "note": "identical accounts trade the same signals: risk does not diversify; firm limits on simultaneous accounts / allocation must be checked"}


def store(c: sqlite3.Connection, name: str, result: dict) -> int:
    with tx(c):
        return c.execute("INSERT INTO income_scenarios (name, assumptions, results, ts) VALUES (?,?,?,?)",
                         (name, json.dumps({k: result.get(k) for k in ("scenario", "plan", "assumptions")}, default=str), json.dumps(result, default=str), now())).lastrowid
