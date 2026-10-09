"""Forensic audit of the v1 report: quantify inconsistencies (results/audit/audit_v1.json)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.prop_simulation import simulator as S
from qpl.research import pipeline as P, registry as R

ROOT = Path(__file__).resolve().parents[1]
F = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
out = {}
ctx = P.context("dukascopy", "US100", "M15"); days = P.trading_days(ctx)
tr = P.backtest("noise_area", ctx, F, get("NQ"))
nq = P.usd(tr, get("NQ"), contracts=1); mnq = P.usd(tr, get("MNQ"), contracts=1)
for name, (a, b) in {"dev": ("2013-01-01", "2020-12-31"), "oos": ("2021-01-01", "2023-09-11")}.items():
    mn = P.split_metrics(nq, days, {"p": (a, b)})["p"]; mm = P.split_metrics(mnq, days, {"p": (a, b)})["p"]
    out[f"nq_vs_mnq_{name}"] = {"NQ_total": mn["total_usd"], "NQ_total_div10": mn["total_usd"] / 10, "MNQ_total_exact": mm["total_usd"],
                                "NQ_maxdd_div10": mn["max_dd_usd"] / 10, "MNQ_maxdd_exact": mm["max_dd_usd"],
                                "NQ_sharpe": mn["sharpe"], "MNQ_sharpe": mm["sharpe"],
                                "cost_per_rt_NQ": get("NQ").cost_per_rt(), "cost_per_rt_10MNQ": 10 * get("MNQ").cost_per_rt()}
# experiment counting
valid = "decision not like '%superseded%' and decision!='invalid' and stage not like 'audit%'"
rows = R.query(f"select hypothesis_id, instrument, params, stage from experiments where {valid}")
uniq = {(h, i, p) for h, i, p, s in rows}
out["experiment_counting"] = {"ledger_rows_valid": len(rows), "unique_variants_valid": len(uniq),
                              "ledger_rows_all": R.count(), "note": "v1 headline counted ledger rows; several rows per variant (one per split/stage)"}
# pass probability variants
v1 = json.load(open(ROOT / "results_v1_snapshot" / "prop_h3_mnq.json"))
sc = json.load(open(ROOT / "results_v1_snapshot" / "prop_scenarios.json"))
out["pass_prob_variants_topstep50k"] = {
    "conservative_dev_2013_2020_h500": v1["conservative|dev"]["rules"]["Topstep 50K Combine"]["mc"]["p_pass"],
    "conservative_oos_2021_2023_h500": v1["conservative|oos"]["rules"]["Topstep 50K Combine"]["mc"]["p_pass"],
    "scenario_full_edge_2013_2023_h750": sc["scenarios"]["keep_100pct_edge"]["Topstep 50K Combine"]["p_pass"],
    "hist_starts_oos": v1["conservative|oos"]["rules"]["Topstep 50K Combine"]["hist"]["p_pass"],
    "realised_2025_26_mc": sc["realised_2025_26"]["Topstep 50K Combine"]["p_pass"],
    "realised_2025_26_hist_resolved_n": sc["realised_2025_26"]["Topstep 50K Combine"]["hist_starts"]["n_starts"],
    "mc_standard_error_at_p0.75_n4000": float(np.sqrt(0.75 * 0.25 / 4000))}
# historical-start bias: share of starts unresolved (dropped in v1)
d, _ = __import__("prop_eval").sized_daily("noise_area", F, "US100", "MNQ", 500.0)
for name, (a, b) in {"oos": ("2021-01-01", "2023-09-11")}.items():
    x = d.loc[a:b]; r = S.topstep_50k(); tot = 0; unres = 0
    for s in range(0, len(x), 3):
        o, dd, td, fp = S.run_eval(x.pnl.to_numpy()[s:], x.worst.to_numpy()[s:], x.ntrades.to_numpy()[s:], r.start, r.target, r.mll,
                                   r.mll_type, r.lock_at_start, r.dll, r.dll_fail, r.consistency, r.min_days, r.max_days)
        tot += 1; unres += (o == S.TIMEOUT)
    out[f"hist_starts_unresolved_{name}"] = {"starts": tot, "unresolved_dropped": unres}
(ROOT / "results" / "audit" / "audit_v1.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
