"""V7 diagnostics: H3 overlap, coefficients, cost stress, by-year, C/threshold neighbourhood (2016-20 decides)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import factory as F, pipeline as P
from qpl.statistics import tests as T
from qpl.strategies import ml_intraday as ML

ROOT = Path(__file__).resolve().parents[1]
c = P.context("dukascopy", "US100", "M15"); e = P.context("dukascopy", "US500", "M15")
D = ML.features(c, e)
days = pd.DatetimeIndex(sorted(D["date"].unique()))
out = {"neighbourhood": {}}
for Cc in (0.01, 0.1, 1.0):
    p, coefs = ML.walk_forward(D, C=Cc)
    for thr in (0.03, 0.045, 0.06, 0.08):
        d = ML.daily_usd(ML.trades(D, p, thr), days)
        out["neighbourhood"][f"C{Cc}_thr{thr}"] = {per: float(d.loc[a:b].mean() / d.loc[a:b].std() * np.sqrt(252))
                                                   for per, (a, b) in {"wf16_20": ("2016", "2020"), "wf21_23": ("2021", "2023-09-11")}.items()}
    if Cc == 0.1:
        out["coefficients_by_refit_year"] = coefs
        p01 = p
# frozen choice made on 2016-20 only: C=0.1, thr=0.06 (pre-specified grid centre; see v3_gen8_stat)
first = ML.trades(D, p01, 0.06)
d = ML.daily_usd(first, days)
out["frozen"] = {"C": 0.1, "thr": 0.06}
for lab, cm in (("1x", 1), ("2x", 2), ("3x", 3)):
    dd = ML.daily_usd(first, days, cost_mult=cm)
    out[f"cost_{lab}"] = {per: float(dd.loc[a:b].mean() / dd.loc[a:b].std() * np.sqrt(252)) for per, (a, b) in {"wf16_20": ("2016", "2020"), "wf21_23": ("2021", "2023-09-11")}.items()}
out["by_year"] = {int(k): float(v) for k, v in d.groupby(d.index.year).sum().items()}
out["long_short"] = {"long_n": int((first.pos > 0).sum()), "short_n": int((first.pos < 0).sum()),
                     "long_pnl": float(((first.pos * first.y_ret)[first.pos > 0]).sum() * 19900 * 20),
                     "short_pnl": float(((first.pos * first.y_ret)[first.pos < 0]).sum() * 19900 * 20)}
out["entry_slot_counts"] = first.slot.value_counts().sort_index().to_dict()
# overlap with H3 (daily P&L correlation and same-direction share)
inst = get("NQ")
h3 = A.daily_pnl(P.usd(P.backtest("noise_area", c, dict(lookback=14, mult=1.25, trail="band_mean", check_min=60), inst), inst, contracts=1), P.trading_days(c))["pnl"]
j = pd.concat([d, h3.reindex(d.index)], axis=1, keys=["v7", "h3"]).fillna(0).loc["2016":"2023-09-11"]
out["corr_with_h3_daily"] = float(j.corr().iloc[0, 1])
out["stats_wf16_20"] = T.summary_tests(d.loc["2016":"2020"], n_trials=12)
out["stats_wf21_23"] = T.summary_tests(d.loc["2021":"2023-09-11"], n_trials=1)
(ROOT / "results" / "v3_v7_diagnostics.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "experiment", "hypothesis_id": "V7_ML_INTRADAY", "stage": "diagnostics", "summary": {k: v for k, v in out.items() if k not in ("coefficients_by_refit_year",)}})
print(json.dumps(out, indent=1, default=float)[:6000])
