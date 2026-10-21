"""Gen277 (config/gen277_protocol.json): Upbit + Bithumb Korean premium replacing v8.1's alt-kimchi sleeve. Writes results/gen277.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END; MORE = L.ROOT / "research_data/more"; days = pd.date_range("2020-01-01", END); fx = RL.usdkrw()


def kp(venue, c, bn):
    f = MORE / f"{venue}_KRW-{c}_1h.parquet"
    if not f.exists():
        return None
    x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index)
    fxh = fx.shift(1).reindex(x.index.floor("D"), method="ffill").set_axis(x.index)
    p = (x / fxh / bn.reindex(x.index) - 1).dropna().loc[:END + " 23:00"]; p = p[p.index.hour == 23]; p.index = p.index.floor("D")
    return p.reindex(days)


W = {}; used = []
for c in AK.coins():
    bn = B.k5(c).close.resample("1h").last()
    u, b = kp("upbit", c, bn), kp("bithumb", c, bn)
    k = u if b is None else pd.concat([u, b], axis=1).mean(axis=1).where(u.notna() | b.notna())
    if b is not None:
        used.append(c)
    z = (k - k.rolling(30, min_periods=20).mean()) / k.rolling(30, min_periods=20).std()
    W[c] = np.where(z > 1, 0.1, np.where(z < -1, -0.1, 0.0))
W = pd.DataFrame(W, index=days)
bk = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, L.perp(W).rename("alt kimchi")], axis=1).fillna(0.0))[0]
B1, k1 = L.sh(bk, "2022-01-01", END), L.per(bk, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "coins with Bithumb": used,
       "two-venue alt kimchi": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen277.json", "w"), indent=1)
