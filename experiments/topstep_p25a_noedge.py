"""P25a: Topstep 50K pass probability for ZERO-edge strategies at the user's MNQ fees (config/topstep_gen25_protocol.json)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.prop_simulation import simulator as S
from qpl.research import factory as F
rng = np.random.default_rng(25)
COST_RT = 1.22 + 2 * 0.50                     # MNQ: user fee + 1 tick ($0.50) slippage per side
N = 6000
out = {}
for rules in (S.topstep_50k(False), S.topstep_50k(True)):
    rr = {}
    for sigma in (150, 250, 400, 600):
        for tpd in (1, 4):
            cont = sigma / 400.0 * 1.0                               # ~1 MNQ per $400/day of sigma
            cost = COST_RT * cont * tpd
            pnl = rng.normal(-cost, sigma, N)
            worst = np.minimum(0, pnl) * 1.3 - np.abs(rng.normal(0, 0.2 * sigma, N))
            df = pd.DataFrame({"pnl": pnl, "worst": np.minimum(worst, 0), "ntrades": np.full(N, tpd)})
            m = S.monte_carlo(df, rules, n_sims=4000, horizon=500, block=1, seed=1)
            rr[f"gauss_sigma{sigma}_tpd{tpd}"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k in ("p_pass", "p_fail", "days_to_pass_p50", "expected_cost_to_pass_usd")}
    for R, b in ((300, 2.0), (500, 2.0), (500, 3.0), (800, 2.0)):          # 'bold' one-trade-per-day, zero gross edge
        p = 1 / (1 + b)
        win = rng.random(N) < p
        cost = COST_RT * R / 200.0                                         # contracts ~ R / $200 stop
        pnl = np.where(win, b * R, -R) - cost
        worst = np.where(win, -0.5 * R, -R) - cost
        df = pd.DataFrame({"pnl": pnl, "worst": worst, "ntrades": np.ones(N, int)})
        m = S.monte_carlo(df, rules, n_sims=4000, horizon=500, block=1, seed=2)
        rr[f"bold_R{R}_b{b}"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k in ("p_pass", "p_fail", "days_to_pass_p50", "expected_cost_to_pass_usd")}
    out[rules.name] = rr
json.dump(out, open("results/topstep_p25a_noedge.json", "w"), indent=1)
F.append({"kind": "analysis", "stage": "P25a_no_edge_benchmark", "result_file": "results/topstep_p25a_noedge.json"})
for k, v in out.items():
    print(k); [print("  ", kk, vv) for kk, vv in v.items()]
