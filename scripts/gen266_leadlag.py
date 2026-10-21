"""Gen266 (config/gen266_protocol.json): hourly Upbit -> Binance lead-lag. Writes results/gen266.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END
fx = RL.usdkrw(); legs = []; n_sig = 0
for c in ["BTC", "ETH"] + AK.coins():
    up = pd.read_parquet(L.ROOT / f"research_data/more/upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index)
    h = B.k5(c).close.resample("1h").last().loc[:END + " 23:00"]; r = h.pct_change(fill_method=None).fillna(0.0)
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    p = (np.log(up / fxh) - np.log(h.reindex(up.index))).reindex(h.index)
    dp = p.diff(); sd = dp.rolling(720, min_periods=480).std().shift(1)
    sig = np.sign(dp.where(dp.abs() > 3 * sd)).fillna(0.0).to_numpy()
    pos = np.zeros(len(h))
    for i in np.flatnonzero(sig):
        pos[i + 1:i + 5] = 0.1 * sig[i]; n_sig += 1
    pos = pd.Series(pos, index=h.index)
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(h.index).fillna(0.0)
    legs.append(pos * r - pos * f - pos.diff().abs().fillna(0.0) * 5 / 1e4)
out = {"reference v8": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "signals": n_sig}
L.judge("Upbit -> Binance hourly lead-lag", pd.concat(legs, axis=1).fillna(0.0).sum(axis=1), out)
json.dump(out, open(L.ROOT / "results/gen266.json", "w"), indent=1)
