"""V6: has the futures trend/carry premium decayed over 50 years? (descriptive; uses all periods, no selection)
Rolling 5y Sharpe, HAC regression of annual Sharpe on time, pre/post-2010 comparison, Bayesian-free change point (ruptures PELT on
annual returns), and per-asset-class trend contribution by decade."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, ruptures as rpt, statsmodels.api as sm
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB
from qpl.data import futures_panel as FP
from qpl.research import factory as F
from qpl.strategies import futures_factors as FF
ROOT = Path(__file__).resolve().parents[1]
sl = pd.read_parquet(ROOT / "results/v6_sleeves_pnl.parquet")
out = {}
for k in ("T", "C", "B0"):
    x = sl[k].loc["1980":"2023"]
    ann = x.groupby(x.index.year).apply(lambda v: v.mean() / v.std() * 16)
    X = sm.add_constant(np.arange(len(ann)))
    m = sm.OLS(ann.to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    algo = rpt.Pelt(model="l2", min_size=5).fit(ann.to_numpy().reshape(-1, 1))
    bk = algo.predict(pen=3 * ann.var())
    out[k] = {"annual_sharpe_slope_per_decade": float(m.params[1] * 10), "slope_t": float(m.tvalues[1]),
              "mean_by_decade": {f"{d}s": round(float(ann[(ann.index >= d) & (ann.index < d + 10)].mean()), 2) for d in (1980, 1990, 2000, 2010, 2020)},
              "pelt_breaks": [int(ann.index[i - 1]) for i in bk[:-1]],
              "pre2010_sharpe": float(x.loc[:"2009"].mean() / x.loc[:"2009"].std() * 16), "post2010_sharpe": float(x.loc["2010":].mean() / x.loc["2010":].std() * 16)}
# per asset class trend Sharpe by decade (TSMOM ensemble, instruments within class only)
P = FP.build(); U, ut = FP.universe(P); ret, cost = P["ret"][U], P["cost"][U]
cls = ut.loc[U, "asset_class"]
pc = {}
for c in ["Equity", "Bond", "FX", "Ags", "Metals", "OilGas"]:
    names = cls[cls == c].index.tolist()
    d = PB.run(ret[names], FF.tsmom(ret[names]), cost[names])["net"]
    pc[c] = {f"{dd}s": round(PB.stats(d.loc[str(dd):str(dd + 9)])["sharpe"], 2) for dd in (1980, 1990, 2000, 2010, 2020)}
out["tsmom_by_class_decade"] = pc
(ROOT / "results/v6_trend_decay.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "stage": "v6_trend_decay", "result_file": "results/v6_trend_decay.json"})
print(json.dumps({k: out[k] for k in ("T", "C", "B0")}, indent=1)); print(pd.DataFrame(pc).T)
