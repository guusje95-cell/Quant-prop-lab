"""Gen312 (config/gen312_protocol.json): BTC/ETH kimchi sleeve in v8.4 and bf2.3. Writes results/gen312.json."""
import json
import numpy as np
import pandas as pd
import ridge_live as RL
import v7lab as L
import bf2lab as F
from qpl.lab import binance_pack as B
END = L.END
z = pd.DataFrame({c: RL.zk_strict(c, B.k5(c).close.loc[:END + " 23:55"].resample("1h").last()) for c in ("BTC", "ETH")}).loc[:END]
w = pd.DataFrame(np.where(z > 1, 0.5, np.where(z < -1, -0.5, 0.0)), index=z.index, columns=z.columns)
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()],
       "share of days in a position": float((w != 0).any(axis=1).mean())}
L.judge("kimchi BTC/ETH v8.4", L.perp(w), out, dev_start="2020-01-01")
F.judge("kimchi BTC/ETH bf2.3", F.cfd(w), out, dev_start="2020-01-01")
json.dump(out, open(L.ROOT / "results/gen312.json", "w"), indent=1)
