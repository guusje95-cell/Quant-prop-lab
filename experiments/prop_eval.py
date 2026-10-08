"""Prop-firm evaluation simulation for a frozen candidate.

Sizing: volatility-scaled micro contracts. contracts = round_down(risk_budget / (sd_pts * point_value)),
minimum 1 (never skip a signal), capped at the firm's position limit. sd_pts = 20-day std of daily
RTH close-to-close changes (known at the prior close), deployment-normalized.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A  # noqa: E402
from qpl.instruments import get  # noqa: E402
from qpl.prop_simulation import simulator as S  # noqa: E402
from qpl.research import pipeline as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def sized_daily(strategy, frozen, proxy, micro, risk_budget, max_contracts=50, cost_mult=1.0, slip_mult=1.0,
                source="dukascopy", tf="M15"):
    ctx = P.context(source, proxy, tf)
    days = P.trading_days(ctx)
    inst = get(micro)
    tr = P.backtest(strategy, ctx, frozen, inst)
    t = P.normalize(tr, P.REF_PRICE[micro]) if source == "dukascopy" else tr
    sd = t["risk_pts"].to_numpy()          # strategy risk_ref = daily sd (points) for noise_area
    q = np.floor(risk_budget / (sd * inst.point_value))
    q = np.where(np.isfinite(q), q, 1)
    q = np.clip(q, 1, max_contracts).astype(np.int64)
    u = A.to_usd(t, inst, q, cost_mult=cost_mult, slip_mult=slip_mult)
    d = A.daily_pnl(u, days)
    return d, u


def run(strategy, frozen, proxy, micro, periods, risk_levels, rules_list, n_sims=4000, tag="cand"):
    """Risk budgets are defined for a $2,000 max-loss account and scaled by MLL/2000 for larger
    accounts; position caps follow the account (50K: 50 micros, 100K: 100, 150K: 150)."""
    out = {}
    for rname, budget in risk_levels.items():
        for pname, (a, b) in periods.items():
            key = f"{rname}|{pname}"
            out[key] = {"budget_per_sd_50k": budget, "rules": {}}
            for rules in rules_list:
                scale = rules.mll / 2000.0 if not micro.endswith("CFD") else 1.0
                cap = int(50 * rules.start / 50_000) if not micro.endswith("CFD") else 10**7
                d_all, u = sized_daily(strategy, frozen, proxy, micro, budget * scale, max_contracts=cap)
                d = d_all.loc[a:b]
                mc = S.monte_carlo(d, rules, n_sims=n_sims, horizon=500, block=5)
                hs = S.historical_starts(d, rules, step=3)
                uu = u[(u.day >= a) & (u.day <= b)]
                out[key]["rules"][rules.name] = {"mc": mc, "hist": hs, "avg_contracts": float(uu["qty"].mean()),
                                                 "daily_mean": float(d["pnl"].mean()), "daily_sd": float(d["pnl"].std()),
                                                 "worst_intraday": float(d["worst"].min())}
    (ROOT / "results" / f"prop_{tag}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def show(out):
    for key, v in out.items():
        print(f"== {key}")
        for rn, r in v["rules"].items():
            mc, hs = r["mc"], r["hist"]
            print(f"   {rn:28s} q={r['avg_contracts']:.1f} mu={r['daily_mean']:.0f} sd={r['daily_sd']:.0f} MC pass={mc['p_pass']:.2f} fail={mc['p_fail']:.2f} (mll {mc['p_fail_mll']:.2f}) timeout={mc['p_timeout']:.2f} "
                  f"days p50={mc['days_to_pass_p50']:.0f} p90~{mc['days_to_pass_p95']:.0f} cost=${mc.get('expected_cost_to_pass_usd', float('nan')):.0f} | "
                  f"HIST pass={hs['p_pass']:.2f} n={hs['n_starts']} p50days={hs['days_to_pass_p50']:.0f}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "h3"
    if which == "h3":
        frozen = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
        periods = {"dev": ("2013-01-01", "2020-12-31"), "oos": ("2021-01-01", "2023-09-11")}
        risk = {"conservative": 500.0, "moderate": 1000.0, "aggressive": 1600.0}
        rules = [S.topstep_50k(), S.topstep_50k(dll=True), S.topstep_100k(), S.topstep_150k(), S.mffu_50k_core()]
        out = run("noise_area", frozen, "US100", "MNQ", periods, risk, rules, tag="h3_mnq")
        show(out)
    if which == "h3_ftmo":
        frozen = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
        periods = {"dev": ("2013-01-01", "2020-12-31"), "oos": ("2021-01-01", "2023-09-11")}
        # budget = USD per 1 daily sd of the underlying; strategy daily sd ~ 1/3 of it
        risk = {"conservative": 2000.0, "moderate": 3500.0, "aggressive": 5000.0}
        out = run("noise_area", frozen, "US100", "US100CFD", periods, risk, [S.ftmo_2step_100k()], tag="h3_ftmo")
        show(out)
