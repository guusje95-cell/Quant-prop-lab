"""CFT two-speed pipeline backtest engine (what happens if you buy N challenges?).

Usage:
    python scripts/cft_pipeline_backtest.py                      # default: $100k 1-Phase, fee $798, budgets 1,2,3,5,10
    python scripts/cft_pipeline_backtest.py --account 50000 --fee 399 --program 1PHASE --budgets 1 3 5 --horizon 730

Policy (frozen, gen34): challenge = E2 on 10 majors at 15% vol; funded = E2 on BTC+ETH at 6% vol (1-Phase; 2-Phase funded 8%).
Outcomes over (a) every historical start date (every 5 days, 2018-01 .. data end - horizon) and (b) 1,000 stationary
block-bootstrap market histories. Writes results/cft_pipeline_backtest.json (used by the dashboard)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
src = (ROOT / "experiments/crypto_gen34_twospeed.py").read_text().split("out = {")[0]
G = {"__name__": "g34", "__file__": str(ROOT / "experiments/crypto_gen34_twospeed.py")}
exec(compile(src, "g34", "exec"), G)
from qpl.prop_simulation.cft_ledger import run_ledger  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402

arrs, idx, unit = G["arrs"], G["idx"], G["unit"]
POLICY = {"1PHASE": {"v_c": 0.15, "v_f": 0.06}, "2PHASE": {"v_c": 0.20, "v_f": 0.08}}


def summarize(runs, horizon):
    net = np.array([r["net"] for r in runs]); W = np.vstack([np.pad(r["wealth"], (0, horizon - len(r["wealth"])), "edge") for r in runs])
    fp = [r["first_payout_day"] for r in runs]
    q = lambda a, p: float(np.percentile(a, p))
    curve_days = list(range(0, horizon, 7))
    return {"n_paths": len(runs),
            "P_at_least_one_pass": round(float(np.mean([r["passed"] > 0 for r in runs])), 3),
            "avg_challenges_bought": round(float(np.mean([r["bought"] for r in runs])), 2),
            "avg_passes": round(float(np.mean([r["passed"] for r in runs])), 2),
            "avg_funded_breaches": round(float(np.mean([r["funded_breaches"] for r in runs])), 2),
            "avg_payouts": round(float(np.mean([r["payouts"] for r in runs])), 1),
            "avg_fees_usd": round(float(np.mean([r["fees"] for r in runs])), 0),
            "avg_paid_usd": round(float(np.mean([r["paid"] for r in runs])), 0),
            "net_mean_usd": round(float(net.mean()), 0), "net_p10_usd": round(q(net, 10), 0), "net_p50_usd": round(q(net, 50), 0),
            "net_p90_usd": round(q(net, 90), 0), "P_net_positive": round(float((net > 0).mean()), 3),
            "worst_net_usd": round(float(net.min()), 0), "max_loss_possible_usd": None,
            "median_days_to_first_payout": float(np.median([d for d in fp if d is not None])) if any(d is not None for d in fp) else None,
            "P_payout_within_180d": round(float(np.mean([d is not None and d <= 180 for d in fp])), 3),
            "curve": {"day": curve_days, "p10": [round(q(W[:, d], 10)) for d in curve_days], "p50": [round(q(W[:, d], 50)) for d in curve_days],
                      "p90": [round(q(W[:, d], 90)) for d in curve_days], "mean": [round(float(W[:, d].mean())) for d in curve_days]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", type=float, default=100_000); ap.add_argument("--fee", type=float, default=798)
    ap.add_argument("--program", default="1PHASE", choices=list(POLICY)); ap.add_argument("--budgets", type=int, nargs="+", default=[1, 2, 3, 5, 10])
    ap.add_argument("--horizon", type=int, default=730); ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    pol = POLICY[a.program]
    rc = arrs("MAJ10", pol["v_c"]); rf = arrs("LIQUID2", pol["v_f"])
    starts = [i for i in range(0, len(idx) - a.horizon, 5) if idx[i] >= pd.Timestamp("2018-01-01")]
    bidx = T.stationary_bootstrap_indices(len(idx), a.boot, 20.0, np.random.default_rng(2026))[:, :a.horizon]
    out = {"inputs": {"account_usd": a.account, "fee_usd": a.fee, "program": a.program, "horizon_days": a.horizon, "policy": pol,
                      "split": 0.8, "payout_processing": 0.05, "historical_starts": [str(idx[starts[0]].date()), str(idx[starts[-1]].date())]},
           "scenarios": {}}
    for B in a.budgets:
        hist = [run_ledger(*rc, *rf, s, a.program, a.account, a.fee, B, a.horizon) for s in starts]
        boot = [run_ledger(*(x[b] for x in rc), *(x[b] for x in rf), 0, a.program, a.account, a.fee, B, a.horizon) for b in bidx]
        out["scenarios"][str(B)] = {"historical": summarize(hist, a.horizon), "bootstrap": summarize(boot, a.horizon)}
        h, b = out["scenarios"][str(B)]["historical"], out["scenarios"][str(B)]["bootstrap"]
        print(f"budget {B:>2}: P(pass>=1) hist {h['P_at_least_one_pass']:.0%} boot {b['P_at_least_one_pass']:.0%} | bought {h['avg_challenges_bought']} "
              f"passes {h['avg_passes']} | fees ${h['avg_fees_usd']:,.0f} paid ${h['avg_paid_usd']:,.0f} | net mean ${h['net_mean_usd']:,.0f} "
              f"(p10 {h['net_p10_usd']:,.0f} / p50 {h['net_p50_usd']:,.0f} / p90 {h['net_p90_usd']:,.0f}) boot mean ${b['net_mean_usd']:,.0f} "
              f"P(net>0) {h['P_net_positive']:.0%}/{b['P_net_positive']:.0%}", flush=True)
    # strategy equity curves (for the dashboard)
    curves = {}
    for name, key, v in (("challenge_MAJ10_v15", "MAJ10", pol["v_c"]), ("funded_BTCETH_v6", "LIQUID2", pol["v_f"])):
        x = unit[key]["net"] * v; eq = (1 + x).cumprod()
        m = (1 + x).resample("ME").prod() - 1
        curves[name] = {"weekly_equity": {str(k.date()): round(float(val), 4) for k, val in eq.resample("W").last().items()},
                        "monthly": {str(k.date())[:7]: round(float(val), 4) for k, val in m.items()},
                        "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "max_dd": round(float((eq / eq.cummax() - 1).min()), 4),
                        "sharpe": round(float(x.mean() / x.std() * np.sqrt(365)), 2), "worst_day": round(float((unit[key]["worst"] * v).min()), 4)}
    C = pd.read_pickle(ROOT / "results/crypto_gen38_Cstar_series.pkl")["net"]
    eq = (1 + C).cumprod(); m = (1 + C).resample("ME").prod() - 1
    curves["personal_Cstar"] = {"weekly_equity": {str(k.date()): round(float(val), 4) for k, val in eq.resample("W").last().items()},
                                "monthly": {str(k.date())[:7]: round(float(val), 4) for k, val in m.items()},
                                "cagr": round(float(eq.iloc[-1] ** (365 / len(C)) - 1), 4), "max_dd": round(float((eq / eq.cummax() - 1).min()), 4),
                                "sharpe": round(float(C.mean() / C.std() * np.sqrt(365)), 2)}
    out["strategy_curves"] = curves
    (ROOT / "results/cft_pipeline_backtest.json").write_text(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
