"""Gen307 (config/gen307_protocol.json): v8.4 + Coinbase premium sleeve on perps. Writes results/gen307.json."""
import json
import numpy as np
import v7lab as L
import cfd_book as CB
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
w = CB.coinbase_premium_w(L.END + " 23:00")[["BTC", "ETH"]]
L.judge("coinbase premium (perps)", L.perp(w), out, dev_start="2020-01-01")
json.dump(out, open(L.ROOT / "results/gen307.json", "w"), indent=1)
