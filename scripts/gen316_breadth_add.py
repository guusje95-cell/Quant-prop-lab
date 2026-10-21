"""Gen316 (config/gen316_protocol.json): v8.4 + 60-coin invvol premium carry as an added sleeve. Writes results/gen316.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
w = CS.premium_breadth_weights(invvol=True)
h = CS.premium_carry_breadth(w=w).loc[:END + " 23:00"]
L.judge("premium carry 60 invvol (added)", h, out, dev_start="2020-01-01")
# descriptive: 2x costs (extra 5 bp per unit turnover)
turn = w.diff().abs().sum(axis=1)
h2 = h - (turn.reindex(h.index.floor("D")).set_axis(h.index).where(h.index.hour == 0, 0.0).fillna(0.0) * 5 / 1e4)
b2 = L.book([h2.reindex(L.H6.index).fillna(0.0).rename("premium carry 60")])
out["2x costs (descriptive)"] = [round(L.sh(b2, "2022-01-01", END), 3), np.round(L.per(b2, "2022-01-01"), 3).tolist()]
print(out["2x costs (descriptive)"]); json.dump(out, open(L.ROOT / "results/gen316.json", "w"), indent=1)
