"""Gen282 (config/gen282_protocol.json): euro-area premium (BTC, ETH) vs v8.1. Writes results/gen282.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END; days = pd.date_range("2020-01-01", END); MORE = L.ROOT / "research_data/more"; FIAT = L.ROOT / "research_data/binance_fiat"
fx0 = pd.read_parquet(MORE / "yahoo_EURUSD_1d.parquet")["close"]
lt = pd.DatetimeIndex(fx0.index).tz_localize("UTC").tz_convert("Europe/London"); ld = lt.normalize()
order = pd.Series(lt == ld).reset_index(drop=True).sort_values(kind="stable").index
fx = pd.Series(fx0.to_numpy()[order], index=ld[order].tz_localize(None)); fx = fx[~fx.index.duplicated(keep="last")].sort_index()
W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    x = pd.read_parquet(FIAT / f"{c}EUR_1h.parquet")["close"]; x.index = pd.DatetimeIndex(x.index)
    fxh = fx.shift(1).reindex(x.index.floor("D"), method="ffill").set_axis(x.index)
    bn = B.k5(c).close.resample("1h").last().reindex(x.index)
    p = (x * fxh / bn - 1).loc[:END + " 23:00"]; p24 = p.rolling(24, min_periods=20).mean()
    z = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std(); z = z[z.index.hour == 23]; z.index = z.index.floor("D")
    z = z.reindex(days); W[c] = np.where(z > 1, 0.25, np.where(z < -1, -0.25, 0.0))
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
L.judge("euro-area premium", L.perp(W), out); json.dump(out, open(L.ROOT / "results/gen282.json", "w"), indent=1)
