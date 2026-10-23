"""Gen334 (config/gen334_protocol.json): funding-change XS, low-beta XS and BTC/ETH late-UTC seasonality as added sleeves in
v8.6, strict rule. Writes results/gen334.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END
coins = CS._breadth_universe(); H = CS._breadth_close(coins); P = H.resample("1D").last()
listed = P.notna().cumsum() >= 60; dr = P.pct_change(fill_method=None); vol = dr.rolling(30).std()
pk = [c for c in coins if c in B.coins()]
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fd = fund.resample("1D").sum().reindex(P.index)


def xs_w(score):
    rk = score.where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed)
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
    return CS._hold(w.fillna(0.0), 7, True)


f7 = fd.rolling(7).mean()
A = xs_w(-(f7 - f7.shift(7)))
beta = dr.rolling(60, min_periods=50).cov(dr["BTC"]).div(dr["BTC"].rolling(60, min_periods=50).var(), axis=0)
Bw = xs_w(-beta.drop(columns=[]))
out = {"reference v8.6": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}


def strict(name):
    r = out[name]; b, k = r["v7"]
    r["strict"] = bool(r["pass"] and k[0] >= L.REF[1][0] and b >= L.REF[0] + 0.05); print(name, "strict", r["strict"], flush=True)


for k, w in (("A funding-change XS", A), ("B low-beta XS", Bw)):
    L.judge(k, CS.premium_carry_breadth(coins=coins, w=w).loc[:END + " 23:00"], out, dev_start="2020-01-01"); strict(k)
# C: long BTC / ETH 0.5 each in the 22:00 and 23:00 UTC bars (bars stamped at the open), 5 bp per side, funding
hc = H[["BTC", "ETH"]]; rr = hc.pct_change(fill_method=None).fillna(0.0)
pos = pd.DataFrame(0.0, index=hc.index, columns=hc.columns); pos[hc.index.hour.isin([22, 23])] = 0.5
fh = fund[["BTC", "ETH"]].copy(); fh.index = fh.index - pd.Timedelta(hours=1); fh = fh.groupby(level=0).sum().reindex(hc.index).fillna(0.0)
C = (pos * rr).sum(axis=1) - (pos * fh).sum(axis=1) - pos.diff().abs().fillna(0.0).sum(axis=1) * 5 / 1e4
L.judge("C late-UTC BTC/ETH seasonality", C.loc[:END + " 23:00"], out, dev_start="2020-01-01"); strict("C late-UTC BTC/ETH seasonality")
json.dump(out, open(L.ROOT / "results/gen334.json", "w"), indent=1)
