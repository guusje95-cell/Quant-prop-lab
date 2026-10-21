"""Gen264 (config/gen264_protocol.json): idiosyncratic altcoin premium XS; kimchi bubble reversal. Writes results/gen264.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END
out = {"reference v8": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; save = lambda: json.dump(out, open(L.ROOT / "results/gen264.json", "w"), indent=1)
days = pd.date_range("2020-01-01", END); fx = RL.usdkrw()


def kp_daily(c):
    up = pd.read_parquet(L.ROOT / f"research_data/more/upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index)
    bn = B.k5(c).close.resample("1h").last(); fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END + " 23:00"]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    return kd.reindex(days)


z = lambda s: (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()
alts = AK.coins(); kb = kp_daily("BTC")
IP = pd.DataFrame({c: z(kp_daily(c) - kb) for c in alts})
L.judge("A idiosyncratic altcoin premium XS", L.perp(L.xs(IP)), out); save()
ZK = AK.zscores(END + " 23:00").reindex(days)
QV = B.panel("quote_volume", "1D", alts).reindex(days).replace(0, np.nan); fxd = fx.shift(1).reindex(days, method="ffill")
att = {}
for c in alts:
    u = pd.read_parquet(L.ROOT / f"research_data/more/upbit_KRW-{c}_1h.parquet"); u.index = pd.DatetimeIndex(u.index)
    sh_ = ((u["close"] * u["volume"]).groupby(u.index.floor("D")).sum().reindex(days) / fxd / QV[c]).replace(0, np.nan)
    m7 = sh_.rolling(7, min_periods=5).mean(); att[c] = (m7 - sh_.rolling(90, min_periods=60).mean()) / sh_.rolling(90, min_periods=60).std()
A = pd.DataFrame(att)
W = pd.DataFrame(np.where((ZK > 1) & (A > 1), -0.1, 0.0), index=days, columns=alts)
out["B bubble days (coin-days)"] = int((W != 0).sum().sum())
L.judge("B kimchi bubble reversal", L.perp(W), out); save()
