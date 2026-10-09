"""Audit V4-C1 correction: recompute cross-timeframe comparisons with realized-time daily labels."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF, factory as F
from qpl.strategies import crypto as CS
ROOT = Path(__file__).resolve().parents[1]
f, _ = CF.btc_funding()
b1, b4, bh1 = CD.btc_bars("1D").loc["2014-06-01":], CD.btc_bars("4h").loc["2014-06-01":], CD.btc_bars("1h").loc["2019-06-01":]
ct1 = VB.daily(VB.run(b1, CS.trend_ensemble(b1, {}), 7.0, f), at="realized")["net"]
bh = VB.daily(VB.run(b1, CS.buy_hold_vt(b1, {}), 7.0, f), at="realized")["net"]
out = {"C11_corr_with_CT1_2015_21": {}, "C6_train_residual_realized": {}}
for L in (30, 90, 180):
    d = VB.daily(VB.run(b4, CS.tsmom(b4, {"lookback": L, "vol_lb": 180}), 7.0, f), at="realized")["net"]
    out["C11_corr_with_CT1_2015_21"][L] = float(d.loc["2015":"2021"].corr(ct1.loc["2015":"2021"]))
fb = CD.funding_binance_2020_2024("BTC")
for q in (0.90, 0.95):
    for h in (24, 72):
        d = VB.daily(VB.run(bh1, CS.funding_contrarian(bh1, {"q": q, "hold": h, "lb_settlements": 270}, fb), 7.0, f), at="realized")["net"]
        x, y = d.loc["2020-07-01":"2021-12-31"].align(bh.loc["2020-07-01":"2021-12-31"], join="inner")
        beta = np.cov(x, y)[0, 1] / y.var()
        out["C6_train_residual_realized"][f"q{q}_h{h}"] = {"sharpe": VB.stats(x)["sharpe"], "residual": VB.stats(x - beta * y)["sharpe"], "beta": float(beta)}
(ROOT / "results/v4_audit_c1_correction.json").write_text(json.dumps(out, indent=1))
F.append({"kind": "correction", "audit_id": "V4-C1", "affects": ["C6 residual Sharpe (verdict unchanged: fails 3/4-positive gate)", "C11 correlation with CT1"],
          "result": out})
print(json.dumps(out, indent=1))
