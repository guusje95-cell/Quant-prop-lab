"""Phase 6: sizing policies vs Topstep 50K outcomes under three edge regimes for H3 (1 MNQ unit trades).
Shows whether sizing can rescue a weak edge (it must not be used to promote one)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.instruments import get  # noqa: E402
from qpl.prop_simulation import policy_sim as PS  # noqa: E402
from qpl.research import factory as F, pipeline as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
inst = get("MNQ")


def day_lists(u, days):
    g = {d: list(zip(x.pnl_usd, x.mae_usd)) for d, x in u.groupby("day")}
    return [g.get(d, []) for d in days]


ctx = P.context("dukascopy", "US100", "M15"); days = P.trading_days(ctx)
u = P.usd(P.backtest("noise_area", ctx, FROZEN, inst), inst, contracts=1)
u = u[(u.day >= "2013-01-01") & (u.day <= "2023-09-11")]
dd = days[(days >= "2013-01-01") & (days <= "2023-09-11")]
mu, sd, n = u.pnl_usd.mean(), u.pnl_usd.std(), len(u)
regimes = {"historical_full_edge": u.copy()}
h = u.copy(); h["pnl_usd"] -= 0.5 * mu; h["mae_usd"] -= 0.5 * mu; regimes["half_edge"] = h
z = u.copy(); z["pnl_usd"] -= mu; z["mae_usd"] -= mu; regimes["zero_edge"] = z
c2 = P.context("topstepx", "MNQ", "1h", 540, 960); d2 = P.trading_days(c2)
u2 = P.usd(P.backtest("noise_area", c2, FROZEN, inst), inst, contracts=1, norm=False)
u2 = u2[(u2.day >= "2025-03-21")]
regimes["realised_2025_26"] = u2
d2 = d2[d2 >= "2025-03-21"]

mu_lo_dev = mu - 1.2816 * sd / np.sqrt(n)                       # one-sided 90% lower bound, 2013-2023
mu_lo_recent = u2.pnl_usd.mean() - 1.2816 * u2.pnl_usd.std() / np.sqrt(len(u2))
POLICIES = {
    "fixed_1": lambda: PS.fixed(1), "fixed_2": lambda: PS.fixed(2), "fixed_3": lambda: PS.fixed(3),
    "dd_aware_2to1": lambda: PS.drawdown_aware(2, 1, 0.5),
    "daily_stop300_fixed1": lambda: PS.daily_stop(PS.fixed(1), 300.0),
    "daily_stop300_fixed2": lambda: PS.daily_stop(PS.fixed(2), 300.0),
    "kelly_q_lowerbound_hist": lambda: PS.kelly_uncertainty(mu_lo_dev, sd ** 2, 0.25),
    "kelly_full_lowerbound_hist": lambda: PS.kelly_uncertainty(mu_lo_dev, sd ** 2, 1.0),
    "kelly_q_lowerbound_recent": lambda: PS.kelly_uncertainty(mu_lo_recent, u2.pnl_usd.var(), 0.25),
}
out = {"per_trade_stats": {"mu": mu, "sd": sd, "n": n, "mu_lo90_hist": mu_lo_dev, "mu_recent": u2.pnl_usd.mean(),
                           "mu_lo90_recent": mu_lo_recent, "n_recent": len(u2),
                           "full_kelly_contracts_at_2000_cushion_hist": mu_lo_dev / sd ** 2 * 2000}, "results": {}}
for rname, uu in regimes.items():
    dl = day_lists(uu, d2 if rname == "realised_2025_26" else dd)
    for pname, pf in POLICIES.items():
        r = PS.monte_carlo(dl, pf, n=2000, horizon=750)
        out["results"][f"{rname}|{pname}"] = r
        print(rname, pname, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
(ROOT / "results" / "v3_sizing.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "experiment", "hypothesis_id": "SIZING_H3", "summary": out["per_trade_stats"],
          "results": {k: v["p_pass"] for k, v in out["results"].items()}})
print(json.dumps(out["per_trade_stats"], indent=1, default=float))
