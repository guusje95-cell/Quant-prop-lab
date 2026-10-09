"""Why did H3 fail in 2025-26? Descriptive diagnostics (no strategy tuning):
 1. intraday trendiness by year: variance ratio of the 10:00->16:00 move vs hourly returns, and the
    correlation of the 09:30->11:00 move with the 11:00->16:00 move (momentum persistence);
 2. sampling: how often did a 13-month pooled ES/NQ/YM H3 Sharpe <= the 2025-26 value occur historically?
CFD (2013-2023) uses Dukascopy H1 bars; futures (2025-26) use TopstepX 1h bars (same hourly grid)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A  # noqa: E402
from qpl.instruments import get  # noqa: E402
from qpl.research import factory as F, pipeline as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
out = {"trendiness": {}, "sampling": {}}


def trend_stats(ctx):
    rth = (ctx.rth & ctx.valid_day).to_numpy()
    df = pd.DataFrame({"d": ctx["date"].to_numpy(), "et": ctx.et_min.to_numpy(), "o": ctx.open.to_numpy(), "c": ctx.close.to_numpy()})[rth]
    rows = []
    for d, g in df.groupby("d"):
        g = g.set_index("et")
        if not {600, 660, 900}.issubset(g.index):
            continue
        p10, p11, p16 = g.loc[600, "o"], g.loc[660, "o"], g.loc[900, "c"]
        hr = np.log(g.c / g.o).loc[600:900]
        rows.append({"d": pd.Timestamp(d), "am": np.log(p11 / g.iloc[0].o), "pm": np.log(p16 / p11),
                     "full": np.log(p16 / p10), "hr_var": float((hr ** 2).sum()), "nh": len(hr)})
    x = pd.DataFrame(rows).set_index("d")
    return x


def summarize(x):
    return {"days": len(x), "variance_ratio": float((x.full ** 2).mean() / x.hr_var.mean()),
            "corr_am_pm": float(x.am.corr(x.pm)), "beta_pm_on_am": float(np.polyfit(x.am, x.pm, 1)[0])}


for fut, proxy in (("NQ", "US100"), ("ES", "US500"), ("YM", "US30")):
    x = trend_stats(P.context("dukascopy", proxy, "H1", 540, 960))
    out["trendiness"][f"{fut}_cfd"] = {str(y): summarize(g) for y, g in x.groupby(x.index.year) if len(g) > 100}
    out["trendiness"][f"{fut}_cfd"]["2013-2023"] = summarize(x)
    xf = trend_stats(P.context("topstepx", fut, "1h", 540, 960))
    out["trendiness"][f"{fut}_futures_2025_26"] = summarize(xf.loc["2025-03-21":])

# sampling: historical distribution of 13-month pooled (vol-scaled) H3 Sharpe across ES/NQ/YM (CFD)
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
cols = {}
for fut, proxy in (("NQ", "US100"), ("ES", "US500"), ("YM", "US30")):
    c = P.context("dukascopy", proxy, "H1", 540, 960)
    inst = get(fut)
    cols[fut] = A.daily_pnl(P.usd(P.backtest("noise_area", c, FROZEN, inst), inst, contracts=1), P.trading_days(c))["pnl"]
D = pd.DataFrame(cols).loc["2013-09":"2023-09-11"].fillna(0)
pooled = (D / D.std()).mean(axis=1)
roll = pooled.rolling(270).apply(lambda z: z.mean() / z.std() * np.sqrt(252)).dropna()
fut_pooled = json.load(open(ROOT / "results" / "v3_holdout_crossmarket.json"))["pooled_B_sharpe"]
out["sampling"] = {"pooled_ES_NQ_YM_270d_sharpe_pcts": {q: float(np.percentile(roll, q)) for q in (1, 5, 25, 50)},
                   "observed_2025_26_pooled_ES_YM_RTY": fut_pooled,
                   "historical_frac_le_observed": float((roll <= fut_pooled).mean()),
                   "min_historical": float(roll.min())}
(ROOT / "results" / "v3_decay_diagnostics.json").write_text(json.dumps(out, indent=1))
F.append({"kind": "experiment", "hypothesis_id": "H3_DECAY_DIAG", "summary": out})
for k, v in out["trendiness"].items():
    if "cfd" in k:
        print(k, {y: (round(s["variance_ratio"], 2), round(s["corr_am_pm"], 3)) for y, s in v.items()})
    else:
        print(k, round(v["variance_ratio"], 2), round(v["corr_am_pm"], 3), v["days"])
print(json.dumps(out["sampling"], indent=1))
