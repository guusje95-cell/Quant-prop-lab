"""CT1 sizing, uncertainty-adjusted Kelly, DSR and stress tests. The rule is FROZEN; only sizing/stress are studied.
Post-development sample (OOS+holdout, 2022-01-01..2026-10-09) is the conservative return distribution."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import crypto as CD  # noqa: E402
from qpl.research import crypto_factory as CF, factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import crypto as CS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
b = CD.btc_bars("1D").loc["2014-06-01":]
fund, _ = CF.btc_funding()
w = CS.trend_ensemble(b, {})
POST = ("2022-01-01", "2026-10-09")
DEV = ("2015-01-01", "2021-12-31")


def net(wt, cost=7.0, f=fund):
    return VB.daily(VB.run(b, wt, cost, f), at="realized")["net"]


base = net(w)
post, dev = base.loc[POST[0]:POST[1]], base.loc[DEV[0]:DEV[1]]
out: dict = {"post_dev_stats": VB.stats(post), "dev_stats": VB.stats(dev)}

# ---- multiple-testing context: unique crypto variants evaluated before the CT1 holdout look
seen = set()
for line in open(ROOT / "research_database/ledger.jsonl"):
    e = json.loads(line)
    if e.get("kind") == "experiment" and e.get("asset_class") == "crypto" and "LOOK" not in str(e.get("stage")):
        seen.add((e["hypothesis_id"], json.dumps(e.get("params"), sort_keys=True), e.get("rule"), e.get("cost_bps")))
    if e.get("kind") == "holdout_evaluation" and e.get("hypothesis_id") == "CT1_TREND_ENSEMBLE":
        break
n_trials = len(seen)
x = dev.to_numpy()
out["selection"] = {"n_crypto_variants_before_holdout": n_trials,
                    "PSR_dev": T.probabilistic_sharpe(x), "DSR_dev": T.deflated_sharpe(x, n_trials),
                    "PSR_post": T.probabilistic_sharpe(post.to_numpy()),
                    "post_sharpe_ci95": T.bootstrap_ci(post.to_numpy(), T.sharpe, n_boot=2000, block=20)[:2]}
# T.sharpe annualises with sqrt(252); rescale CI to sqrt(365)
out["selection"]["post_sharpe_ci95"] = [v * np.sqrt(365 / 252) for v in out["selection"]["post_sharpe_ci95"]]

# ---- uncertainty-adjusted Kelly (daily, fraction of the 40%-vol-target book)
mu, var = post.mean(), post.var()
rng = np.random.default_rng(11)
idx = T.stationary_bootstrap_indices(len(post), 2000, 20, rng)
mus = np.array([post.to_numpy()[i].mean() for i in idx])
out["kelly"] = {"full_kelly_multiple_of_book": float(mu / var), "half_kelly": float(mu / var / 2),
                "kelly_at_mu_p25": float(max(np.quantile(mus, 0.25), 0) / var), "kelly_at_mu_p05": float(max(np.quantile(mus, 0.05), 0) / var),
                "P(mu<=0)": float(np.mean(mus <= 0)),
                "note": "multiple of the 40%-vol book: 1.0 = 40% annual vol. Values < 1 mean de-lever."}

# ---- 1-year bootstrap paths at different vol targets (linear scaling of the 40% book; cap effects ignored)
def paths(r: np.ndarray, scale: float, haircut: float = 0.0, n=4000, L=365, seed=5):
    r = r - haircut * r.mean()
    ii = T.stationary_bootstrap_indices(len(r), n, 20, np.random.default_rng(seed))[:, :L]
    P = r[ii] * scale
    eq = P.cumsum(axis=1)
    dd = (eq - np.maximum.accumulate(eq, axis=1)).min(axis=1)
    fin = eq[:, -1]
    return {"median_1y": float(np.median(fin)), "p05_1y": float(np.quantile(fin, 0.05)), "P(loss_1y)": float(np.mean(fin < 0)),
            "P(maxDD<-10%)": float(np.mean(dd < -0.10)), "P(maxDD<-20%)": float(np.mean(dd < -0.20)), "P(maxDD<-30%)": float(np.mean(dd < -0.30)),
            "median_maxDD": float(np.median(dd))}


r = post.to_numpy()
out["sizing_paths"] = {f"vol{tv}": {"base": paths(r, tv / 40), "expectancy_-50%": paths(r, tv / 40, 0.5), "expectancy_-100%": paths(r, tv / 40, 1.0)}
                       for tv in (10, 15, 20, 30, 40)}

# ---- stress tests on the post-development sample (40% book)
def s(x):
    st = VB.stats(x.loc[POST[0]:POST[1]])
    return {k: round(st[k], 4) for k in ("sharpe", "ann_ret", "max_dd", "worst_day")}


stress = {"base_7bps": s(base), "cost_14bps": s(net(w, 14)), "cost_21bps": s(net(w, 21)), "cost_30bps": s(net(w, 30)),
          "extra_1day_delay": s(net(w.shift(1).fillna(0))),
          "funding_+2bp_per_8h": s(net(w, 7, fund + 0.0002)),
          "spot_only_no_shorts_15bps": s(net(w.clip(lower=0), 15, None))}
outs = []
for seed in range(20):                      # 5% of days the rebalance fails (outage): previous weight is held
    m = np.random.default_rng(seed).random(len(w)) < 0.05
    ww = w.copy(); ww[m] = np.nan; ww = ww.ffill().fillna(0)
    outs.append(VB.stats(net(ww).loc[POST[0]:POST[1]])["sharpe"])
stress["outage_5pct_days_median_sharpe"] = float(np.median(outs))
# gap risk: largest BTC daily moves and CT1 exposure into them (position cap 1.0 => loss <= |move|)
rb = np.log(b["close"]).diff()
worst = rb.nsmallest(5)
stress["worst_btc_days"] = {str(k.date()): {"btc_logret": round(float(v), 3), "ct1_w_prev": round(float(w.shift(1).get(k, np.nan)), 3)} for k, v in worst.items()}
stress["max_abs_position"] = float(w.abs().max())
out["stress"] = stress
out["leverage_note"] = ("Max |w| = {:.2f} of equity. At 1x notional, fully collateralised (isolated margin = notional), a perp position cannot be "
                        "liquidated by a single-day move < 100%. At 3x leverage, liquidation occurs near a 30% adverse move (minus maintenance margin); "
                        "BTC fell ~40% intraday on 2020-03-12/13. Recommendation: <= 1x notional, no cross-margin with other positions.").format(stress["max_abs_position"])
out["recommendation"] = ("Paper-trade at 10-15% annual vol target (0.25-0.375x the research book). Uncertainty-adjusted Kelly at the 25th-percentile mean "
                         "is the relevant cap; full Kelly is not justified because P(mu<=0) in the post-development sample is material.")
(ROOT / "results/v4_ct1_risk.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "hypothesis_id": "CT1_TREND_ENSEMBLE", "stage": "sizing_stress", "result_file": "results/v4_ct1_risk.json",
          "summary": {"kelly": out["kelly"], "selection": out["selection"]}})
print(json.dumps({k: out[k] for k in ("post_dev_stats", "selection", "kelly", "stress")}, indent=1, default=float))
print(json.dumps({k: v["base"] for k, v in out["sizing_paths"].items()}, indent=1))
print(json.dumps({k: v["expectancy_-50%"] for k, v in out["sizing_paths"].items()}, indent=1))
