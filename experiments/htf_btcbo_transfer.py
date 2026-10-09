"""Single-use cross-coin transfer test of frozen HTFD_A2_BO_PW (config/htf_btcbo_transfer_protocol.json)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.htf import core as H
from qpl.research import factory as F
COINS = {"ethusdt": "ETHUSDT", "adausdt": "ADAUSDT", "bnb": "BNBUSDT", "doge": "DOGEUSDT", "etcusdt": "ETCUSDT", "link": "LINKUSDT",
         "ltc": "LTCUSDT", "matic": "MATICUSDT", "sol": "SOLUSDT", "uni": "UNIUSDT", "xrp": "XRPUSDT"}
def run(cmult):
    series, per = [], {}
    for folder, sym in COINS.items():
        raw = pd.read_csv(f"data/raw/dukascopy/crypto/{folder}/{sym}_D1.csv", sep="\t"); raw.columns = [c.lower() for c in raw.columns]
        d = raw.set_index(pd.DatetimeIndex(pd.to_datetime(raw["time"], utc=True)))[["open", "high", "low", "close"]].astype(float).sort_index()
        d = d[~d.index.duplicated()].loc[:"2023-09-08"]
        bps = (14 if sym == "ETHUSDT" else 20) * cmult / 1e4; cf = lambda p, b=bps: b * p
        ev = [e for e in H.detect_events(d, H.htf_frame(d, "crypto"), "PW") if e.strategy == "A2_BO"]
        t = H.simulate(d, ev, cf, hold=5)
        if len(t) == 0: continue
        m = H.daily_mtm(d, t, cf); m.index = m.index.normalize().tz_localize(None)
        series.append(m.groupby(level=0).sum())
        per[sym] = {"trades": len(t), "exp_R": round(float(t.R_net.mean()), 3), "long_R": round(float(t[t.dir > 0].R_net.mean()), 3),
                    "short_R": round(float(t[t.dir < 0].R_net.mean()), 3), "start": str(d.index[0].date())}
    p = pd.concat(series, axis=1, sort=True).fillna(0).sum(axis=1)
    return float(p.mean() / p.std() * np.sqrt(365)), per, p
sh1, per, p = run(1.0); sh2, _, _ = run(2.0)
share = float(np.mean([v["exp_R"] > 0 for v in per.values()]))
res = {"pooled_sharpe_1x": sh1, "pooled_sharpe_2x": sh2, "share_coins_positive": share, "per_coin": per,
       "by_year_R": {int(y): round(float(v), 2) for y, v in p.groupby(p.index.year).sum().items()},
       "pass": bool(sh1 > 0.3 and share >= 0.6 and sh2 > 0)}
F.append({"kind": "holdout_evaluation", "hypothesis_id": "HTFD_A2_BO_PW_BTC", "protocol": "config/htf_btcbo_transfer_protocol.json",
          "result": {k: res[k] for k in ("pooled_sharpe_1x", "pooled_sharpe_2x", "share_coins_positive", "pass")}})
Path("results/htf_btcbo_transfer.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
