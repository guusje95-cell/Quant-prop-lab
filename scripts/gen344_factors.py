"""Gen344 (config/gen344_protocol.json): size, MAX and illiquidity XS factors on the 60-coin universe. Writes results/gen344.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); H = CS._breadth_close(coins); P = H.resample("1D").last()
listed = P.notna().cumsum() >= 60; dr = P.pct_change(fill_method=None); vol = dr.rolling(30).std()
pk = [c for c in coins if c in B.coins()]
qv = pd.concat([B.panel("quote_volume", "1D", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["quote_volume"].rename(c)
                                                      .pipe(lambda z: z.groupby(pd.DatetimeIndex(z.index).floor("D")).sum()) for c in coins if c not in pk], axis=1)
qv = qv[~qv.index.duplicated()].reindex(P.index)[coins].replace(0, np.nan)


def xs_w(score):
    rk = score.where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed)
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
    return CS._hold(w.fillna(0.0), 7, True)


S = {"A size": -np.log(qv.rolling(30, min_periods=20).mean()), "B MAX": -dr.rolling(30, min_periods=20).max(),
     "C illiquidity": (dr.abs() / qv).rolling(30, min_periods=20).mean()}
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {"reference v8.6": [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()}
R = out["reference v8.6"]
for nm, sc in S.items():
    h = CS.premium_carry_breadth(coins=coins, w=xs_w(sc)).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
    s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    cc = float(pd.concat([h.groupby(h.index.floor("D")).sum(), L.ALTK[-1].groupby(L.ALTK[-1].index.floor("D")).sum()], axis=1).loc["2022":END].corr().iloc[0, 1])
    b = L.book([h.rename(nm)]); k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr carry 60": round(cc, 3),
               "orthogonal candidate": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2), "v8.6 with it": k,
               "strict pass": bool(all(a >= q for a, q in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05)}
    print(nm, out[nm], flush=True)
json.dump(out, open(ROOT / "results/gen344.json", "w"), indent=1)
