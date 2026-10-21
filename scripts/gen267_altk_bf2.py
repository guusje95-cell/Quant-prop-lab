"""Gen267 (config/gen267_protocol.json): v8 altcoin kimchi in bf2 on all 16 BrightFunded altcoins. Writes results/gen267.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import alt_kimchi as AK
from qpl.lab import binance_pack as B
END = F.END
w = AK.weights(END + " 23:00"); coins = list(w.columns)
H = B.panel("close", "1h", coins).loc[:END + " 23:00"]; r = H.pct_change(fill_method=None).fillna(0.0)
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
turn = held.diff().abs().fillna(held.abs()).sum(axis=1)
h = ((held * r).sum(axis=1) - turn * (10.0 + 1.2) / 1e4).reindex(F.IDXbf).fillna(0.0)
out = {"reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "coins": coins}
F.judge("alt kimchi, 16 BrightFunded altcoins", h, out)
json.dump(out, open(F.ROOT / "results/gen267.json", "w"), indent=1)
