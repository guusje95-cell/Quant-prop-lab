"""Gen269 (config/gen269_protocol.json): altcoin demand composite (kimchi + Coinbase premium), replacing v8's alt kimchi; vs v8.1.
Writes results/gen269.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import alt_kimchi as AK
B, END = L.B, L.END
days = pd.date_range("2020-01-01", END); ZK = AK.zscores(END + " 23:00").reindex(days); comp = {}; has_cb = []
for c in ZK.columns:
    f = L.ROOT / f"research_data/coinbase/{c}-USD_1h.parquet"
    if f.exists():
        cb = pd.read_parquet(f)["close"]; cb.index = pd.DatetimeIndex(cb.index); bn = B.k5(c).close.resample("1h").last().loc[:END + " 23:00"]
        pr = (cb / bn.reindex(cb.index) - 1).dropna(); p24 = pr.rolling(24, min_periods=20).mean()
        zc = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
        zc = zc[zc.index.hour == 23]; zc.index = zc.index.floor("D"); zc = zc.reindex(days)
        comp[c] = pd.concat([ZK[c], zc], axis=1).mean(axis=1, skipna=True).where(ZK[c].notna() | zc.notna()); has_cb.append(c)
    else:
        comp[c] = ZK[c]
Z = pd.DataFrame(comp); W = pd.DataFrame(np.where(Z > 1, 0.1, np.where(Z < -1, -0.1, 0.0)), index=days, columns=Z.columns)
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "coins with Coinbase": has_cb}
h = L.perp(W).rename("alt demand composite")
# replaces the alt kimchi sleeve: build the book without L.ALTK
b = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, h], axis=1).fillna(0.0))[0]
s = L.per(h, "2020-01-01"); c_ = float(pd.concat([L.CST, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1])
B1, k1 = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
r = {"sleeve D/T/H": np.round(s, 3).tolist(), "corr C*": round(c_, 3), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
r["pass"] = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and c_ <= 0.3 and B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])
out["alt demand composite (replaces alt kimchi)"] = r; print(r)
json.dump(out, open(L.ROOT / "results/gen269.json", "w"), indent=1)
