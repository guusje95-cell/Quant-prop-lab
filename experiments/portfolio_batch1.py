"""Descriptive portfolio check (all inputs are already-viewed periods): F9 futures + BTC weekly-level breakout (MTM) + CT1.
Weekly alignment 2015-01..2024-03; each sleeve scaled to 10% vol using TRAILING 52-week vol (point-in-time), equal risk."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.htf import core as H
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF
from qpl.strategies import crypto as CS
f9 = pd.read_parquet("results/v6_f9_pnl.parquet")["net"]
d = pd.read_parquet("data/processed/crypto/bitstamp_btcusd_1D.parquet")[["open", "high", "low", "close"]].loc["2014-06-01":]
ev = [e for e in H.detect_events(d, H.htf_frame(d, "crypto"), "PW") if e.strategy == "A2_BO"]
t = H.simulate(d, ev, lambda p: 0.0014 * p, hold=5)
bo = H.daily_mtm(d, t, lambda p: 0.0014 * p); bo.index = bo.index.tz_localize(None)
bars = CD.btc_bars("1D").loc["2014-06-01":]; fu, _ = CF.btc_funding()
ct1 = VB.daily(VB.run(bars, CS.trend_ensemble(bars, {}), 7.0, fu), at="realized")["net"]; ct1.index = ct1.index.tz_localize(None)
W = pd.DataFrame({"F9": f9, "BTC_BO_PW": bo, "CT1": ct1}).loc["2015-01-01":"2024-03-28"].fillna(0).resample("W-FRI").sum()
scaled = W.div(W.rolling(52, min_periods=26).std().shift(1) * np.sqrt(52), axis=1) * 0.10
scaled = scaled.dropna()
sh = lambda x: float(x.mean() / x.std() * np.sqrt(52))
mdd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min())
out = {"corr": scaled.corr().round(2).to_dict(), "single": {k: {"sharpe": round(sh(scaled[k]), 2), "max_dd": round(mdd(scaled[k]), 3)} for k in scaled}}
for name, cols in {"F9+BO": ["F9", "BTC_BO_PW"], "F9+CT1": ["F9", "CT1"], "F9+BO+CT1": ["F9", "BTC_BO_PW", "CT1"]}.items():
    p = scaled[cols].mean(axis=1)
    out[name] = {"sharpe": round(sh(p), 2), "max_dd": round(mdd(p), 3), "by_period": {k: round(sh(p.loc[a:z]), 2) for k, (a, z) in {"2015-19": ("2015", "2019"), "2020-24Q1": ("2020", "2024")}.items()}}
out["note"] = "descriptive; all periods previously viewed; crypto sleeve Sharpe dominated by 2015-21"
json.dump(out, open("results/portfolio_batch1.json", "w"), indent=1)
print(json.dumps(out, indent=1))
