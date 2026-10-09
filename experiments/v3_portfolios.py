"""Ranked multi-strategy portfolios (all components EXPLORATORY or REJECTED; descriptive only)."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import factory as F, pipeline as P
from qpl.statistics import metrics as M
from qpl.strategies import v3_intraday  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
H3 = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
H4 = dict(entry_min=1140, exit_min=180, stop_atr=1.0)
V11 = dict(asia_start=1140, asia_end=180, exit_min=660, stop_frac=float("nan"))
comp = {"H3_MNQ": ("noise_area", "US100", "MNQ", H3, (570, 960)), "H3_MES": ("noise_area", "US500", "MES", H3, (570, 960)),
        "H4_MNQ": ("overnight_drift", "US100", "MNQ", H4, (570, 960)), "V11_MGC": ("asian_breakout", "XAUUSD", "MGC", V11, (180, 660))}
S = {}
for k, (st, px, fut, prm, ses) in comp.items():
    ctx = P.context("dukascopy", px, "M15", *ses); inst = get(fut)
    S[k] = A.daily_pnl(P.usd(P.backtest(st, ctx, prm, inst), inst, contracts=1), P.trading_days(ctx))["pnl"]
D = pd.DataFrame(S).loc["2015-04-01":"2023-09-11"].fillna(0)
per = {"dev_2015_2020": ("2015-04-01", "2020-12-31"), "oos_2021_2023": ("2021-01-01", "2023-09-11")}
scale = 1 / D.loc[per["dev_2015_2020"][0]:per["dev_2015_2020"][1]].std()        # equal-vol weights fixed on dev
rows = []
for r in range(1, 5):
    for combo in itertools.combinations(D.columns, r):
        x = (D[list(combo)] * scale[list(combo)]).mean(axis=1)
        row = {"portfolio": "+".join(combo)}
        for pn, (a, b) in per.items():
            y = x.loc[a:b]
            s = M.summarize(y)
            row[f"{pn}_sharpe"] = s["sharpe"]; row[f"{pn}_maxdd_units"] = s["max_dd_usd"]
        rows.append(row)
R_ = pd.DataFrame(rows).sort_values("dev_2015_2020_sharpe", ascending=False)
out = {"corr_dev": D.loc[:"2020"].corr().round(3).to_dict(), "corr_oos": D.loc["2021":].corr().round(3).to_dict(),
       "tail_corr_dev_worst10pct": D.loc[:"2020"][D.loc[:"2020"].sum(axis=1) <= D.loc[:"2020"].sum(axis=1).quantile(0.1)].corr().round(3).to_dict(),
       "ranked": R_.round(3).to_dict("records"), "note": "ranking by DEV Sharpe; OOS shown; components are not validated strategies"}
(ROOT / "results" / "v3_portfolios.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "experiment", "hypothesis_id": "PORTFOLIOS", "summary": {"top": R_.head(5).round(3).to_dict("records")}})
print(R_.round(2).to_string()); print(json.dumps(out["corr_oos"], indent=0))
