"""How much edge is needed to pass Topstep 50K reliably? Synthetic Gaussian daily P&L with given annual Sharpe (net of costs)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.prop_simulation import simulator as S
from qpl.research import factory as F
rng = np.random.default_rng(7); N = 20000; out = {}
for sd in (150, 250, 400):
    for sr in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        mu = sr * sd / np.sqrt(252)
        pnl = rng.normal(mu, sd, N); worst = np.minimum(0, pnl) * 1.3
        m = S.monte_carlo(pd.DataFrame({"pnl": pnl, "worst": worst, "ntrades": 1}), S.topstep_50k(False), n_sims=4000, horizon=500, block=1, seed=1)
        out[f"sd{sd}_SR{sr}"] = {"p_pass": round(m["p_pass"], 3), "days_to_pass_p50": m["days_to_pass_p50"], "cost_to_pass": round(m.get("expected_cost_to_pass_usd", np.nan), 0)}
json.dump(out, open("results/topstep_edge_requirement.json", "w"), indent=1)
F.append({"kind": "analysis", "stage": "topstep_edge_requirement", "result_file": "results/topstep_edge_requirement.json"})
print(pd.DataFrame({k: v for k, v in out.items()}).T.to_string())
