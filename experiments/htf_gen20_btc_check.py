"""Gen20 follow-up (descriptive, no re-selection): is BTC A2_BO_PW just BTC beta or CT1 in disguise?"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.htf import core as H
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF, factory as F
from qpl.strategies import crypto as CS
ROOT = Path(".")
d = pd.read_parquet("data/processed/crypto/bitstamp_btcusd_1D.parquet")[["open", "high", "low", "close"]].loc["2014-06-01":]
lv = H.htf_frame(d, "crypto")
ev = [e for e in H.detect_events(d, lv, "PW") if e.strategy == "A2_BO"]
t = H.simulate(d, ev, lambda p: 0.0014 * p, hold=5)
cal = d.index.tz_convert("UTC").normalize().tz_localize(None)
m = H.daily_mtm(d, t, lambda p: 0.0014 * p); m.index = cal
r = m.groupby(level=0).sum() * H.RISK_PER_TRADE                     # daily MTM % return at 0.25% risk/trade
b = VB.btc_bars("1D") if hasattr(VB, "btc_bars") else None
bars = CD.btc_bars("1D").loc["2014-06-01":]; f, _ = CF.btc_funding()
ct1 = VB.daily(VB.run(bars, CS.trend_ensemble(bars, {}), 7.0, f), at="realized")["net"]; ct1.index = ct1.index.tz_localize(None)
bh = np.log(bars["close"]).diff(); bh.index = bh.index.tz_localize(None)
out = {}
for k, (a, z) in {"DEV": ("2015", "2019"), "VAL": ("2020", "2021"), "TEST": ("2022", "2026")}.items():
    x, y, c = r.loc[a:z], bh.reindex(r.index).loc[a:z].fillna(0), ct1.reindex(r.index).loc[a:z].fillna(0)
    beta = np.cov(x, y)[0, 1] / y.var(); res = x - beta * y
    out[k] = {"sharpe": float(x.mean() / x.std() * np.sqrt(365)), "beta_to_btc": float(beta), "residual_sharpe": float(res.mean() / res.std() * np.sqrt(365)),
              "corr_with_CT1": float(x.corr(c)), "corr_with_btc": float(x.corr(y)), "time_in_market": float((t.set_index("t_entry").loc[a:z].shape[0] * 5) / len(x))}
F.append({"kind": "analysis", "note": "MTM re-measurement (exit-day booking replaced by daily mark-to-market)", "evidence": out}) if False else None
F.append({"kind": "decision", "hypothesis_id": "HTFD_A2_BO_PW_BTC", "verdict": "PROMISING_BUT_UNVALIDATED",
          "reason": "Correction of code verdict: BTC has no fresh holdout (protocol); TEST 2022-26 BTC path previously observed (CT1). DEV/VAL/TEST net Sharpe 0.88/0.75/0.86; see results/htf_gen20_btc_check.json for beta/CT1 overlap",
          "evidence": out})
from qpl.research import registry as R
R.set_verdict("HTFD_A2_BO_PW_BTC", "PROMISING_BUT_UNVALIDATED", "code said ELIGIBLE; corrected: no fresh holdout for BTC, TEST path previously observed")
Path("results/htf_gen20_btc_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
