"""Scale plan within the firms' verified rules (2026-10-30 official pages): HyroTrader one account per program type (Zero-, One-,
Two-Step), CFT not usable from the Netherlands for the crypto book (Bybit platform restricted, MT5 / Match-Trader charge swaps),
BrightFunded swap-free CFD account for the CFD book. Model estimate (presets mostly unverified; HyroTrader aggregate caps unknown).
Crypto and CFD use the SAME bootstrap path (seed) because the books are 0.82 correlated: conservative. Writes results/hub_research/income_scale_plan.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "src"))
from qpl.hub import income
h = pd.read_parquet(ROOT / "results/v98b_book_hourly.parquet")["book"]
HY = [{"preset": "HyroTrader Two-Step $200k", "start_day": 0, "budget": 3}, {"preset": "HyroTrader One-Step $100k", "start_day": 90, "budget": 3},
      {"preset": "HyroTrader Zero-Step $100k", "start_day": 180, "budget": 3}]
BF = [{"preset": "BrightFunded Two-Step Classic $200k", "start_day": 60, "budget": 3}]
out = {"assumptions": __doc__, "rows": []}
def run(plan, sharpe, seed=5):
    sc = dict(income.SCENARIOS["conservative"]); sc["live_sharpe"] = sharpe
    return income.simulate(h, sc, plan, n_paths=300, seed=seed, return_paths=True)["monthly_paths_eur"]
for cs, bs in ((1.65, 1.3), (1.75, 1.3), (1.4, 1.1)):
    for name, plans in (("HyroTrader Two-Step only", [(HY[:1], cs)]), ("HyroTrader 3 program types", [(HY, cs)]),
                        ("HyroTrader 3 + BrightFunded CFD", [(HY, cs), (BF, bs)])):
        M = sum(run(p, s) for p, s in plans); y2 = M[:, 12:24]
        out["rows"].append({"crypto live Sharpe": cs, "CFD live Sharpe": bs, "plan": name, "year-2 mean month EUR": round(float(y2.mean())),
                            "year-2 median month EUR": round(float(np.median(y2))), "P(month >= 10k) year 2": round(float((y2 >= 10_000).mean()), 2),
                            "2-year total p10 / p50 EUR": [round(float(np.percentile(M.sum(axis=1), q))) for q in (10, 50)], "P(2-year loss)": round(float((M.sum(axis=1) < 0).mean()), 2)})
        print(out["rows"][-1], flush=True)
(ROOT / "results/hub_research/income_scale_plan.json").write_text(json.dumps(out, indent=1))
