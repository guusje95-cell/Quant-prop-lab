"""v9.9 S1 (descriptive decision tool, no trials): HyroTrader Two-Step $200k risk choice for v9.8 WITH the total low-cap cap (4.5% of the
initial balance, binding harder at higher risk), at planning-level live Sharpe 1.5 and a weak 1.2. One account, 2 years, 300 bootstrap
paths (hub income engine; preset terms partly unverified; the 40%-a-day consistency rule is not modelled). Writes results/v99/sizing_v98_capped.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.hub import income
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
s, pos, _ = EL.pnl(idx); ph, W, M = CS.portfolio_v5(V7.assign(**{"listing short": s}))
g = pos.abs().sum(axis=1).reindex(idx).fillna(0.0); w = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
rows = []
for risk in (1.0, 1.25, 1.5, 1.75, 2.0):
    k = (0.045 / (g * w * m * 0.902 * risk)).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
    b = CS.portfolio_v5(V7.assign(**{"listing short": s * k}))[0]
    b = b * 0.15 / (dd(b.loc["2022":"2024"]).std() * np.sqrt(365))
    for sh in (1.5, 1.2):
        sc = dict(income.SCENARIOS["conservative"]); sc["live_sharpe"] = sh
        r = income.simulate(b, sc, [{"preset": "HyroTrader Two-Step $200k", "start_day": 0, "budget": 3}], risk=risk, n_paths=300, return_paths=True)
        M2 = r["monthly_paths_eur"]; tot = M2.sum(axis=1)
        rows.append({"risk": risk, "assumed live Sharpe": sh, "2-year net EUR mean": round(float(tot.mean())), "p10": round(float(np.percentile(tot, 10))),
                     "P(2-year loss)": round(float((tot < 0).mean()), 2), "year-2 mean month EUR": round(float(M2[:, 12:24].mean())),
                     "median days to first cash": r["median_days_to_first_cash"]})
        print(rows[-1], flush=True)
(ROOT / "results/v99/sizing_v98_capped.json").write_text(json.dumps({"doc": __doc__, "rows": rows}, indent=1))
