"""V6 falsification audit of gen13 (descriptive; NO rule changes; TEST/HOLDOUT already looked at once).
A1 cross-source price check: pysystemtrade daily returns vs independent Dukascopy CFD/FX daily returns
A2 year-by-year pattern vs known trend-industry history (2008 strong, 2009 weak, 2011-13 weak, 2014 strong, 2022 strong)
A3 asset-class and instrument concentration of P&L
A4 execution-lag sensitivity (lag 1/2/3/5) and cost multiples (1/2/3/5)
A5 universe-size sensitivity (random half-universes) and start-date effect
A6 hourly-era stitching check: return autocorrelation / vol before and after 2013 (when hourly rows begin)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP, loaders  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PR = v6.protocol("v6_futures_protocol.json"); PER = PR["periods"]
P = FP.build(); U, utab = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
classes = utab.loc[U, "asset_class"]
SIG = PB.sigma(ret)
out = {}

# A1 cross-source
pairs = {"SP500": ("dukascopy", "US500"), "NASDAQ": ("dukascopy", "US100"), "GOLD-mini": ("dukascopy", "XAUUSD"), "EUR_mini": ("dukascopy", "EURUSD"),
         "DAX": ("dukascopy", "DE40"), "GBP_micro": ("dukascopy", "GBPUSD"), "BRENT_W": ("dukascopy", "BRENT"), "AUD": ("dukascopy", "AUDUSD"), "DOW": ("dukascopy", "US30")}
a1 = {}
for fut, (src, sym) in pairs.items():
    if fut not in P["ret"].columns:
        continue
    try:
        d = loaders.load(src, sym, "D1")
    except Exception as e:  # noqa: BLE001
        a1[fut] = f"n/a ({e.__class__.__name__})"; continue
    c = d["close"]; c.index = c.index.tz_convert(None).normalize() if c.index.tz is not None else c.index.normalize()
    rc = np.log(c).diff()
    if sym == "USDJPY":
        rc = -rc
    rf = np.log1p(P["ret"][fut])
    j = pd.concat([rf, rc], axis=1, keys=["fut", "cfd"]).dropna().loc["2014":"2023"]
    # weekly to absorb close-time differences between sources
    wk = j.resample("W").sum()
    a1[fut] = {"daily_corr": round(float(j.corr().iloc[0, 1]), 3), "weekly_corr": round(float(wk.corr().iloc[0, 1]), 3),
               "vol_ratio": round(float(j.fut.std() / j.cfd.std()), 3), "n": len(j)}
out["A1_cross_source"] = a1

# primary signals
sigs = {"F1_TSMOM": FF.tsmom(ret), "F2_EWMAC": FF.ewmac(ret), "F3_CARRY": FF.carry(ret, cy, 21)}
sigs["F7_COMBO"] = (sum(s.fillna(0) for s in [FF.ct1_transfer(ret)] + list(sigs.values())) / 4).where(ret.notna().cumsum() > 0)
res = {k: PB.run(ret, s, cost, sig=SIG, return_weights=True) for k, s in sigs.items()}

# A2 by year
out["A2_by_year"] = {k: {int(y): round(float(v), 3) for y, v in d["net"].groupby(d.index.year).sum().loc[1990:].items()} for k, (d, _) in res.items()}

# A3 contribution by class and top instruments (TEST+HOLDOUT, after the looks - descriptive)
a3 = {}
for k, (d, W) in res.items():
    pnl_i = (W.shift(2) * ret.fillna(0))
    for per in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT"):
        x = pnl_i.loc[PER[per][0]:PER[per][1]]
        by_cls = x.T.groupby(classes).sum().T.sum() * PB.ANN / len(x)
        tot = x.sum().sum()
        top = x.sum().sort_values(ascending=False)
        a3.setdefault(k, {})[per] = {"ann_by_class": by_cls.round(4).to_dict(),
                                     "top5_share": round(float(top.head(5).sum() / tot), 2) if tot else None,
                                     "top5": top.head(5).round(4).to_dict(), "share_instruments_positive": round(float((x.sum() > 0).mean()), 2)}
out["A3_concentration"] = a3

# A4 lag and cost sensitivity (all periods reported; protocol lag = 2, cost 1x)
a4 = {}
for k in ("F1_TSMOM", "F3_CARRY", "F7_COMBO"):
    for lag in (1, 2, 3, 5):
        d = PB.run(ret, sigs[k], cost, lag=lag, sig=SIG)
        a4.setdefault(k, {})[f"lag{lag}"] = {p: round(PB.stats(d["net"].loc[PER[p][0]:PER[p][1]])["sharpe"], 2) for p in PER if p != "LATE_HOLDOUT"}
    for cm in (2, 3, 5):
        d = PB.run(ret, sigs[k], cost, cost_mult=cm, sig=SIG)
        a4[k][f"cost{cm}x"] = {p: round(PB.stats(d["net"].loc[PER[p][0]:PER[p][1]])["sharpe"], 2) for p in PER if p != "LATE_HOLDOUT"}
out["A4_lag_cost"] = a4

# A5 random half-universes (structure of dependence on instrument choice)
rng = np.random.default_rng(0)
a5 = []
for i in range(20):
    sub = list(rng.choice(U, size=len(U) // 2, replace=False))
    d = PB.run(ret[sub], FF.tsmom(ret[sub]), cost[sub], sig=SIG[sub])
    a5.append({p: PB.stats(d["net"].loc[PER[p][0]:PER[p][1]])["sharpe"] for p in ("VALIDATION", "TEST", "HOLDOUT")})
a5 = pd.DataFrame(a5)
out["A5_half_universe_tsmom"] = {"median": a5.median().round(2).to_dict(), "min": a5.min().round(2).to_dict(), "max": a5.max().round(2).to_dict()}

# A6 hourly-era stitching: lag-1 autocorrelation and vol of daily returns, pre/post 2013, median over instruments
ac = {}
for per, (a, z) in {"2005-2012": ("2005", "2012"), "2014-2019": ("2014", "2019"), "2020-2024": ("2020", "2024")}.items():
    x = ret.loc[a:z]
    ac[per] = {"median_lag1_autocorr": round(float(x.apply(lambda s: s.autocorr(1)).median()), 3),
               "median_ann_vol": round(float((x.std() * 16).median()), 3)}
out["A6_stitching"] = ac
(ROOT / "results/v6_futures_audit.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "stage": "v6_futures_audit", "result_file": "results/v6_futures_audit.json", "note": "descriptive falsification; no selection"})
print(json.dumps(out["A1_cross_source"], indent=1))
print(pd.DataFrame(out["A2_by_year"]).T.loc[:, [2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]].round(2).to_string())
for k, v in a4.items():
    print(k, pd.DataFrame(v).T.to_string())
print(json.dumps(out["A5_half_universe_tsmom"]), json.dumps(out["A6_stitching"]))
for k in a3:
    print(k, {p: (a3[k][p]["top5_share"], a3[k][p]["share_instruments_positive"], {c: round(v * 100, 2) for c, v in a3[k][p]["ann_by_class"].items()}) for p in ("TEST", "HOLDOUT")})
