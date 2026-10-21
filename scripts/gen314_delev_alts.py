"""Gen314 (config/gen314_protocol.json): deleveraging bounce on altcoins in v8.4 and bf2.3. Writes results/gen314.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
import cfd_book as CB
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = L.END
alts = [c for c in B.coins() if c not in ("BTC", "ETH")]
w = CS.delev_bounce_weights(coins=alts, size=0.1)
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()],
       "coins": alts, "signal coin-days": int((w > 0).sum().sum())}
L.judge("delev bounce alts v8.4", L.perp(w), out, dev_start="2021-12-01")
ac = [c for c in CB.ALT_CFD if c in w.columns]; wa = w[ac]
cost = pd.Series({c: CB.ALT_SPREAD[c] + CB.COMM for c in ac}) / 1e4
r = B.panel("close", "1h", ac).loc[:END + " 23:00"].pct_change(fill_method=None).fillna(0.0)
held = wa.reindex(wa.index.append(pd.DatetimeIndex([wa.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
h = ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)
F.judge("delev bounce alts bf2.3", h, out, dev_start="2021-12-01")
json.dump(out, open(L.ROOT / "results/gen314.json", "w"), indent=1)
