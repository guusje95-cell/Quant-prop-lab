"""Gen287 (config/gen287_protocol.json): Kraken liquidation-flush bounce on BTC (vs v8.1). Writes results/gen287.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END; days = pd.date_range("2020-01-01", END)
lv = pd.read_parquet(L.ROOT / "research_data/kraken/PF_XBTUSD_liquidation-volume_1d.parquet").iloc[:, 0]; lv.index = pd.DatetimeIndex(lv.index).normalize()
x = np.log1p(lv.clip(lower=0)).reindex(days)
z = (x - x.shift(1).rolling(60, min_periods=40).mean()) / x.shift(1).rolling(60, min_periods=40).std()
ret = B.k5("BTC").close.resample("1D").last().reindex(days).pct_change()
sig = ((z > 2) & (ret < 0)).astype(float)
w = sig.rolling(2, min_periods=1).max() * 0.25                        # signal day d (decided at d's close) -> held d+1, d+2
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "signal days": int(sig.sum())}
L.judge("Kraken liquidation flush bounce", L.perp(pd.DataFrame({"BTC": w})), out, dev_start="2022-04-01")
json.dump(out, open(L.ROOT / "results/gen287.json", "w"), indent=1)
