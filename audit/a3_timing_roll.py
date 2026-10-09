"""Audit A3 timing (look-ahead canary on real data) + A4 roll-day return denominator."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.data import futures_panel as FP
from qpl.backtesting import panel as PB
from qpl.strategies import futures_factors as FF
P = FP.build(); U, _ = FP.universe(P); ret, cost = P["ret"][U], P["cost"][U]
s = FF.tsmom(ret)
out = {"A3_lag_canary_sharpe_2005_2024": {}}
for lag in (0, 1, 2):   # lag 0 = earns the return of the decision day itself (cheating); 1 = next row; 2 = production
    d = PB.run(ret, s, cost, lag=lag)["net"].loc["2005":]
    out["A3_lag_canary_sharpe_2005_2024"][f"lag{lag}"] = round(PB.stats(d)["sharpe"], 3)
# A4: on roll days ret = dADJ/PRICE_{t-1} uses the OLD contract price; correct denominator = FORWARD_{t-1} (new contract)
rows = []
for n in ["SP500", "US10", "GOLD", "CRUDE_W", "EUR", "CORN", "BUND", "NATGAS" if "NATGAS" in U else "COPPER"]:
    d = FP.load_instrument(n)
    m = pd.read_csv(FP.SRC / "multiple_prices_csv" / f"{n}.csv", parse_dates=["DATETIME"])
    m["date"] = m.DATETIME.dt.normalize(); m = m.sort_values("DATETIME").groupby("date").last()
    roll = d.PRICE_CONTRACT.ne(d.PRICE_CONTRACT.shift()) & d.PRICE_CONTRACT.shift().notna()
    fwd_prev = m["FORWARD"].reindex(d.index).shift(1)
    r_alt = d.adj.diff() / fwd_prev
    rel = ((d.ret - r_alt).abs())[roll].dropna()
    rows.append({"inst": n, "roll_days": int(roll.sum()), "median_abs_err_bp": round(float(rel.median() * 1e4), 3),
                 "max_abs_err_bp": round(float(rel.max() * 1e4), 2), "sum_err_share_of_total_abs_ret": round(float(rel.sum() / d.ret.abs().sum()), 5)})
out["A4_roll_denominator"] = rows
print(json.dumps(out, indent=1))
