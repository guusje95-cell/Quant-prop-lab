"""Gen31 descriptive robustness for the APPLICABLE 1-Phase configuration (E2 LIQUID2, v=0.06) and the 2-Phase near miss.
Nothing here changes the frozen choice. Bootstrap = stationary blocks (mean 20 d) of the joint (net, worst, best) daily rows 2018-2026."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen31_liquid2.py").read_text().split("SEL_STARTS = ")[0]
G = {"__name__": "g31", "__file__": str(ROOT / "experiments/crypto_gen31_liquid2.py")}
exec(compile(src, "g31", "exec"), G)
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402

E, engine, c, l, sh, stats, prop, SQ = G["E"], G["engine"], G["c"], G["l"], G["sh"], G["stats"], G["prop"], G["SQ"]
w0 = E.raw_weights(c)
L_unit = float(engine(w0)["net"].loc["2018-01-01":"2022-12-31"].std() * SQ)
out = {}
for prog, v, fee in (("1PHASE", 0.06, 0.008), ("2PHASE", 0.08, 0.009)):
    L = v / L_unit
    base = engine(w0 * L)
    res = {}
    # stressed costs/funding on the prop path
    st = engine(w0 * L, 2.0, 1.0)
    p = prop(st, prog, "2023-01-01", "2024-06-30"); res["TEST_prop_stress_costs"] = {k: p[k] for k in ("P_pass", "P_fail_daily", "P_fail_max", "P_unresolved", "E_payout_frac_12m_per_attempt")}
    # one-day execution delay
    dl = engine(w0.shift(1).fillna(0) * L)
    res["delay_1d_TEST_sharpe"] = round(sh(dl["net"].loc["2023":]), 3); res["delay_1d_ALL_sharpe"] = round(sh(dl["net"]), 3)
    p = prop(dl, prog, "2023-01-01", "2024-06-30"); res["delay_1d_TEST_prop"] = {k: p[k] for k in ("P_pass", "P_fail_daily", "P_fail_max", "P_unresolved", "E_payout_frac_12m_per_attempt")}
    # all-period starts
    p = prop(base, prog, "2018-01-01", "2024-06-30"); res["ALL_starts_2018_2024"] = {k: p[k] for k in ("n", "P_pass", "P_fail_daily", "P_fail_max", "P_unresolved", "median_days_to_pass", "E_payout_frac_12m_per_attempt")}
    res["ALL_starts_EV"] = round(0.95 * p["E_payout_frac_12m_per_attempt"] - fee, 4)
    # block bootstrap of challenge outcomes
    X = base[["net", "worst", "best"]].to_numpy(); rng = np.random.default_rng(31); sims = []
    idx = T.stationary_bootstrap_indices(len(X), 2000, 20.0, rng)
    for k in range(2000):
        Y = X[idx[k][:900]]
        sims.append(CFT.simulate_start(Y[:, 0], 0, prog, mode="optimistic", max_days=548, lo=Y[:, 1], hi=Y[:, 2]))
    sb = CFT.summarize(sims)
    res["bootstrap_2000"] = {k: sb[k] for k in ("P_pass", "P_fail_daily", "P_fail_max", "P_unresolved", "median_days_to_pass", "p25_p75_days_to_pass", "funded_survive_12m", "E_payout_frac_12m_per_attempt")}
    res["bootstrap_EV"] = round(0.95 * sb["E_payout_frac_12m_per_attempt"] - fee, 4)
    x = base["net"].to_numpy()
    res["PSR_vs0_2018_2026"] = round(T.probabilistic_sharpe(x, 0.0), 4)
    res["DSR_N112_var1overT"] = round(T.deflated_sharpe(x, 112), 4)
    res["NW_t"] = [round(z, 3) for z in T.newey_west_t(x)]
    out[prog] = res
    print(prog, json.dumps(res), flush=True)
(ROOT / "results/crypto_gen31_robustness.json").write_text(json.dumps(out, indent=1, default=float))
