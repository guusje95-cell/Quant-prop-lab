"""Gen284 (config/gen284_protocol.json): Korean-session premium change -> 09:00-24:00 UTC trade. Writes results/gen284.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END; fx = RL.usdkrw(); legs = []; n = 0
for c in ["BTC", "ETH"] + AK.coins():
    up = pd.read_parquet(L.ROOT / f"research_data/more/upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index)
    h = B.k5(c).close.resample("1h").last().loc[:END + " 23:00"]; r = h.pct_change(fill_method=None).fillna(0.0)
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / h.reindex(up.index) - 1)                         # bar stamped at its open: value at the bar's close
    k9 = kp[kp.index.hour == 8]; k9.index = k9.index.floor("D")       # close of the 08:00 bar = 09:00 UTC
    k0 = kp[kp.index.hour == 23]; k0.index = k0.index.floor("D") + pd.Timedelta(days=1)   # close of the previous 23:00 bar = 00:00
    dk = (k9 - k0.reindex(k9.index)).dropna()
    z = (dk - dk.shift(1).rolling(30, min_periods=20).mean()) / dk.shift(1).rolling(30, min_periods=20).std()
    sig = np.sign(z.where(z.abs() > 1)).fillna(0.0)
    pos = pd.Series(0.0, index=h.index); hrs = h.index.hour >= 9
    pos[hrs] = 0.1 * sig.reindex(h.index.floor("D")).fillna(0.0).to_numpy()[hrs]
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(h.index).fillna(0.0)
    legs.append(pos * r - pos * f - pos.diff().abs().fillna(0.0) * 5 / 1e4); n += int((sig != 0).sum())
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "trades": n}
L.judge("Korean-session premium change", pd.concat(legs, axis=1).fillna(0.0).sum(axis=1), out)
json.dump(out, open(L.ROOT / "results/gen284.json", "w"), indent=1)
