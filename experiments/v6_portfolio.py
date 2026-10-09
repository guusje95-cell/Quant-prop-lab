"""V6 portfolio research (descriptive; all periods already USED): does crypto CT1 add to the futures TREND+CARRY book?
Weekly alignment (crypto trades 7 days, futures 5). Equal-risk and inverse-variance combinations, marginal contribution,
tail dependence, and drawdown overlap. 2015-01..2024-03 overlap."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF, factory as F
from qpl.statistics import tests as T
from qpl.strategies import crypto as CS
ROOT = Path(__file__).resolve().parents[1]
sl = pd.read_parquet(ROOT / "results/v6_sleeves_pnl.parquet")
b = CD.btc_bars("1D").loc["2014-06-01":]; f, _ = CF.btc_funding()
ct1 = VB.daily(VB.run(b, CS.trend_ensemble(b, {}), 7.0, f), at="realized")["net"]
ct1.index = ct1.index.tz_localize(None)
W = pd.DataFrame({"TREND": sl["T"], "CARRY": sl["C"], "B0": sl["B0"], "LONG_RP": sl["LONG_RP"], "CT1": ct1}).loc["2015-01-01":"2024-03-28"]
W = W.fillna(0).resample("W-FRI").sum()
W = W / W.std() * (0.10 / np.sqrt(52))                    # each scaled to 10% ann vol ex-post (descriptive comparison only)
sh = lambda x: float(x.mean() / x.std() * np.sqrt(52))
out = {"weekly_sharpe": {k: sh(W[k]) for k in W}, "corr": W.corr().round(2).to_dict()}
for wct in (0.0, 0.1, 0.2, 1 / 3, 0.5):
    p = (1 - wct) * W["B0"] + wct * W["CT1"]
    out.setdefault("mix_B0_CT1", {})[round(wct, 2)] = {"sharpe": sh(p), "maxdd": float((p.cumsum() - p.cumsum().cummax()).min())}
# tail dependence: correlation in the worst 10% weeks of B0 and of CT1
q = W["B0"].quantile(0.1); out["corr_in_B0_worst10pct"] = float(W.loc[W.B0 <= q, ["B0", "CT1"]].corr().iloc[0, 1])
out["CT1_mean_in_B0_worst10pct_weeks"] = float(W.loc[W.B0 <= q, "CT1"].mean() / W["CT1"].std())
q2 = W["LONG_RP"].quantile(0.1)
out["in_LONG_RP_worst10pct_weeks_mean_z"] = {k: float(W.loc[W.LONG_RP <= q2, k].mean() / W[k].std()) for k in ("TREND", "CARRY", "CT1")}
# bootstrap of Sharpe improvement from adding CT1 at 1/3 risk
x = np.column_stack([W["B0"], (2 / 3) * W["B0"] + (1 / 3) * W["CT1"]])
idx = T.stationary_bootstrap_indices(len(x), 2000, 8, np.random.default_rng(2))
d = np.array([sh(pd.Series(x[i, 1])) - sh(pd.Series(x[i, 0])) for i in idx])
out["add_CT1_third_risk_sharpe_gain"] = {"point": float(d.mean()), "ci90": [float(np.quantile(d, 0.05)), float(np.quantile(d, 0.95))], "P(gain<=0)": float(np.mean(d <= 0))}
out["by_year_sharpe"] = {k: {int(y): round(sh(g), 2) for y, g in W[k].groupby(W.index.year)} for k in ("B0", "CT1")}
(ROOT / "results/v6_portfolio.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "stage": "v6_portfolio_crypto_futures", "result_file": "results/v6_portfolio.json"})
print(json.dumps({k: out[k] for k in out if k != "corr"}, indent=1)); print(pd.DataFrame(out["corr"]))
