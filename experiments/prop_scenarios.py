"""Prop-firm outcomes under edge-decay scenarios (ESTIMATES) and under the realised 2025-26 futures regime."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.prop_simulation import simulator as S
from qpl.research import pipeline as P
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prop_eval import sized_daily  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)


def haircut(d: pd.DataFrame, keep: float) -> pd.DataFrame:
    """Remove (1-keep) of the mean daily P&L on traded days (volatility unchanged)."""
    x = d.copy()
    traded = x["ntrades"] > 0
    shift = (1 - keep) * x.loc[traded, "pnl"].mean()
    x.loc[traded, "pnl"] -= shift
    x.loc[traded, "worst"] = np.minimum(x.loc[traded, "worst"] - shift, 0)
    return x


def main():
    out = {"scenarios": {}, "realised_2025_26": {}}
    rules = [S.topstep_50k(), S.topstep_150k(), S.ftmo_2step_100k()]
    # historical (dev+OOS) daily P&L at conservative sizing
    base = {}
    base["topstep"] = sized_daily("noise_area", FROZEN, "US100", "MNQ", 500.0)[0].loc["2013-01-01":"2023-09-11"]
    base["topstep150"] = sized_daily("noise_area", FROZEN, "US100", "MNQ", 500.0 * 2.25, max_contracts=150)[0].loc["2013-01-01":"2023-09-11"]
    base["ftmo"] = sized_daily("noise_area", FROZEN, "US100", "US100CFD", 2000.0, max_contracts=10**7)[0].loc["2013-01-01":"2023-09-11"]
    for keep in (1.0, 0.75, 0.5, 0.25, 0.0):
        row = {}
        for r, key in zip(rules, ("topstep", "topstep150", "ftmo")):
            d = haircut(base[key], keep)
            mc = S.monte_carlo(d, r, n_sims=4000, horizon=750)
            row[r.name] = {k: mc.get(k) for k in ("p_pass", "p_fail", "p_timeout", "days_to_pass_p50", "days_to_pass_p95",
                                                  "expected_cost_to_pass_usd")}
            row[r.name]["implied_sharpe"] = float(d.pnl.mean() / d.pnl.std() * np.sqrt(252))
        out["scenarios"][f"keep_{int(keep*100)}pct_edge"] = row
    # realised 2025-26 real-futures regime (hourly approximation, 1 MNQ)
    ctx = P.context("topstepx", "MNQ", "1h", 540, 960)
    days = P.trading_days(ctx); inst = get("MNQ")
    u = P.usd(P.backtest("noise_area", ctx, FROZEN, inst), inst, contracts=1, norm=False)
    d = A.daily_pnl(u, days).loc["2025-03-21":"2026-04-15"]
    for r in rules[:1]:
        mc = S.monte_carlo(d, r, n_sims=4000, horizon=750)
        out["realised_2025_26"][r.name] = {k: mc.get(k) for k in ("p_pass", "p_fail", "p_timeout", "days_to_pass_p50", "expected_cost_to_pass_usd")}
        out["realised_2025_26"][r.name]["hist_starts"] = S.historical_starts(d, r, step=1)
    (ROOT / "results" / "prop_scenarios.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    o = main()
    for k, v in o["scenarios"].items():
        print(k)
        for rn, x in v.items():
            print(f"   {rn:24s} SR={x['implied_sharpe']:.2f} pass={x['p_pass']:.2f} fail={x['p_fail']:.2f} timeout={x['p_timeout']:.2f} p50days={x['days_to_pass_p50']} cost=${x.get('expected_cost_to_pass_usd') or float('nan'):.0f}")
    print("realised 2025-26:", json.dumps(o["realised_2025_26"], default=str)[:800])
