"""WHAT-IF (not a firm simulation): daily EWMAC trend on 17 CME markets (close-to-close, overnight+weekend holding) run through
Topstep-50K-style rules (target 3000, EOD-trailing MLL 2000 locked at start, 55% consistency). Answers: would the established
trend edge pass such a challenge IF overnight holding were allowed (e.g. possibly Lucid - rules not supplied).
Upper bound: continuous position sizes (no contract rounding), costs = panel costs; all periods previously viewed."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.data import futures_panel as FP
from qpl.backtesting import panel as PB
from qpl.strategies import futures_factors as FF
from qpl.prop_simulation import simulator as S
from qpl.research import factory as F
P = FP.build(); U, _ = FP.universe(P)
use = [n for n in ['SP500', 'NASDAQ', 'DOW_mini', 'RUSSELL_mini', 'GOLD', 'SILVER', 'CRUDE_W', 'EUR', 'GBP', 'JPY', 'US10', 'US30', 'GAS_US', 'CORN', 'SOYBEAN', 'COPPER', 'AUD'] if n in U]
ret, cost = P["ret"][use], P["cost"][use]
d = PB.run(ret, FF.ewmac(ret), cost)
net = d["net"].resample("B").sum()
worst_frac = net.clip(upper=0) * 1.5                               # intraday excursion proxy
out = {}
for dsd in (100, 150, 200, 300):                                    # target daily $ sd on the 50K account
    k = dsd / net.loc["1990":].std()
    df = pd.DataFrame({"pnl": net * k, "worst": worst_frac * k, "ntrades": 1}).loc["1990":]
    rules = S.topstep_50k(False)
    hist = S.historical_starts(df, rules, step=5, max_days=750)
    post = S.historical_starts(df.loc["2010":], rules, step=5, max_days=750)
    mc = S.monte_carlo(df.loc["2010":].reset_index(drop=True), rules, n_sims=4000, horizon=750, block=20, seed=3)
    pick = lambda m: {x: (round(m[x], 3) if isinstance(m.get(x), float) else m.get(x)) for x in ("p_pass", "p_fail", "days_to_pass_p50", "expected_cost_to_pass_usd", "n_unresolved")}
    out[f"daily_sd_{dsd}"] = {"hist_1990_2024": pick(hist), "hist_2010_2024": pick(post), "bootstrap_2010_2024": pick(mc),
                              "annual_return_usd_2010_2024": round(float(df.loc["2010":, "pnl"].mean() * 252), 0)}
json.dump(out, open("results/whatif_trend_overnight_prop.json", "w"), indent=1)
F.append({"kind": "analysis", "stage": "what-if trend under Topstep-style rules with overnight holding", "result_file": "results/whatif_trend_overnight_prop.json"})
print(json.dumps(out, indent=1))
