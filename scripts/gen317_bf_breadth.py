"""Gen317 (config/gen317_protocol.json): bf2.3 + invvol premium carry on BrightFunded CFDs. Writes results/gen317.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = F.END
spec = pd.read_csv(sorted((F.ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
avail = set(B.coins()) | set(X.coins())
U = sorted(c for c, v in meas.items() if c in avail and 0 < v <= 50)
w = CS.premium_breadth_weights(coins=U, invvol=True)
H = CS._breadth_close(U); r = H.pct_change(fill_method=None).fillna(0.0)
cost = pd.Series({c: 0.5 * meas[c] + 1.2 for c in U}) / 1e4
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).reindex(columns=U).shift(1).reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0)
h = ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)
out = {"reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "universe": U, "n": len(U)}
F.judge("premium carry BF universe invvol (added)", h, out)
json.dump(out, open(F.ROOT / "results/gen317.json", "w"), indent=1)
