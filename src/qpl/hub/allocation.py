"""Multi-account allocation: which combination of crypto prop accounts is worth it, under an assumed live Sharpe.

Candidates = for each firm preset that the compatibility engine does not mark 'incompatible', 0..max_per_firm accounts, started
`gap_days` apart (account k of the whole plan starts at k x gap). All accounts trade the SAME book, so they share one return path
(pass and fail together): adding accounts adds money and fees, not safety. Constraints: maximum total accounts, the fee budget
(the cash reserve you can lose before any payout), and a cap on the share of planned capital at one firm. The output ranks plans
for a conservative objective (highest p10 of 2-year net cash) and an aggressive one (highest mean), and explains the trade-off.
Nominal account size is never treated as loss capacity: the simulator only ever risks the firm's loss limits."""
from __future__ import annotations

import itertools

import pandas as pd

from qpl.hub import income
from qpl.lab import propfirms as PF

CRYPTO_PRESETS = ["HyroTrader Two-Step $200k", "HyroTrader Two-Step $100k", "Crypto Fund Trader 2-Phase $100k", "Breakout Two-Step $100k"]


def optimise(hourly_unit: pd.Series, scenario: dict, presets: list[str] = CRYPTO_PRESETS, max_per_firm: int = 2, max_total: int = 4,
             fee_budget_usd: float = 5000.0, max_firm_share: float = 0.75, gap_days: int = 120, n_paths: int = 150, seed: int = 9) -> dict:
    rows = []
    firms = {p: p.split()[0] for p in presets}
    for counts in itertools.product(range(max_per_firm + 1), repeat=len(presets)):
        n = sum(counts)
        if n == 0 or n > max_total:
            continue
        cap = {}
        for p, k in zip(presets, counts):
            cap[firms[p]] = cap.get(firms[p], 0) + k * PF.PRESETS[p].account
        if max(cap.values()) / sum(cap.values()) > max_firm_share and len([v for v in cap.values() if v]) > 1:
            continue
        fees_worst = sum(k * 3 * PF.PRESETS[p].fee for p, k in zip(presets, counts))          # 3 attempts per account
        if fees_worst > fee_budget_usd * 3:
            continue
        plan, i = [], 0
        for p, k in zip(presets, counts):
            for _ in range(k):
                plan.append({"preset": p, "start_day": i * gap_days, "budget": 3}); i += 1
        r = income.simulate(hourly_unit, scenario, plan, n_paths=n_paths, seed=seed)
        rows.append({"plan": " + ".join(f"{k}x {p}" for p, k in zip(presets, counts) if k), "accounts": n,
                     "net_2y_mean_eur": r["horizon_net_eur_mean"],
                     "net_2y_p10_eur": r["horizon_net_eur_p10_p50_p90"][0], "net_2y_p50_eur": r["horizon_net_eur_p10_p50_p90"][1],
                     "net_2y_p90_eur": r["horizon_net_eur_p10_p50_p90"][2], "year2_mean_month_eur": r["second_year_mean_month_eur"],
                     "P_net_loss": r["P_net_loss_over_horizon"], "worst_cash_p10_eur": r["worst_cumulative_cash_eur_p10"],
                     "fees_if_every_attempt_used_usd": fees_worst})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"status": "no plan satisfies the constraints"}
    cons = df.sort_values(["net_2y_p10_eur", "P_net_loss"], ascending=[False, True]).head(5)
    aggr = df.sort_values("year2_mean_month_eur", ascending=False).head(5)
    return {"scenario": scenario, "constraints": {"max_per_firm": max_per_firm, "max_total": max_total, "fee_budget_usd": fee_budget_usd,
            "max_firm_share": max_firm_share, "gap_days": gap_days}, "conservative_top": cons.to_dict(orient="records"),
            "aggressive_top": aggr.to_dict(orient="records"), "all": df.to_dict(orient="records"),
            "caveats": ["firm presets are unverified project snapshots (see Prop Firm Center)", "accounts share one return path",
                        "firm limits on simultaneous accounts and total allocation are not yet recorded as verified facts"]}
