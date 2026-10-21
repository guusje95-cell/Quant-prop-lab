"""Gen261 (config/gen261_protocol.json): Upbit attention share; spot-vs-perp volume dominance (vs v8). Writes results/gen261.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END
out = {"reference v8": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; save = lambda: json.dump(out, open(L.ROOT / "results/gen261.json", "w"), indent=1)
days = pd.date_range("2020-01-01", END); fx = RL.usdkrw().shift(1)
QV = B.panel("quote_volume", "1D", B.coins()).reindex(days).replace(0, np.nan)
sh_ = {}
for c in AK.coins():
    u = pd.read_parquet(L.ROOT / f"research_data/more/upbit_KRW-{c}_1h.parquet"); u.index = pd.DatetimeIndex(u.index)
    krw = (u["close"] * u["volume"]).groupby(u.index.floor("D")).sum().reindex(days)
    sh_[c] = krw / fx.reindex(days, method="ffill") / QV[c]
S = pd.DataFrame(sh_).replace(0, np.nan)
L.judge("A Upbit attention share", L.perp(L.xs(np.log(S.rolling(7, min_periods=5).mean() / S.rolling(90, min_periods=60).mean()))), out); save()
sp = pd.DataFrame({c: pd.read_parquet(L.ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet")["quote_volume"].pipe(
    lambda z: z.groupby(pd.DatetimeIndex(z.index).floor("D")).sum()) for c in B.coins()}).reindex(days).replace(0, np.nan)
sc = np.log(sp.rolling(7, min_periods=5).sum() / QV.rolling(7, min_periods=5).sum()) - np.log(sp.rolling(90, min_periods=60).sum() / QV.rolling(90, min_periods=60).sum())
L.judge("B spot dominance", L.perp(L.xs(sc)), out); save()
