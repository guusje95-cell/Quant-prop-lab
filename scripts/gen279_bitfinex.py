"""Gen279 (config/gen279_protocol.json): Bitfinex margin positions (vs v8.1). Writes results/gen279.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END; days = pd.date_range("2020-01-01", END); BF = L.ROOT / "research_data/bitfinex"
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
def daily(pair, side):
    s = pd.read_parquet(BF / f"{pair}_{side}_1h.parquet")["size"]; s = s[s.index.hour == 23]; s.index = s.index.floor("D"); return s.reindex(days)
WA = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]); WB = WA.copy()
for c, pair in (("BTC", "tBTCUSD"), ("ETH", "tETHUSD")):
    lg, sh_ = daily(pair, "long"), daily(pair, "short")
    s = np.log(lg) - np.log(lg.shift(7)); z = (s - s.rolling(90, min_periods=60).mean()) / s.rolling(90, min_periods=60).std()
    WA[c] = np.where(z > 1, 0.25, np.where(z < -1, -0.25, 0.0))
    q = np.log(lg / sh_); z2 = (q - q.rolling(30, min_periods=20).mean()) / q.rolling(30, min_periods=20).std()
    WB[c] = np.where(z2 > 1, 0.25, np.where(z2 < -1, -0.25, 0.0))
L.judge("A Bitfinex whale long change", L.perp(WA), out, dev_start="2021-05-01")
L.judge("B Bitfinex long/short ratio", L.perp(WB), out, dev_start="2021-05-01")
json.dump(out, open(L.ROOT / "results/gen279.json", "w"), indent=1)
