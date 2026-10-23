"""Gen345 (config/gen345_protocol.json): stablecoin mint shock, leverage crowding, weekend reversal XS, US-open seasonality.
Writes results/gen345.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
from qpl.lab.data import stablecoin_caps
END = L.END; ROOT = L.ROOT; days = pd.date_range("2019-06-01", END)
mkd = lambda w, c: CS._from_daily_weights(w, c, 5).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
S = {}
# A mint shock (2-day lag: growth of day d-2 used for the decision at the close of d)
cap = stablecoin_caps(); cap = cap.where(cap > 0).loc["2019":]; g = cap.pct_change().shift(2).reindex(days)
sig = (g > 0.005).astype(float).rolling(3, min_periods=1).max()
S["A stablecoin mint shock"] = mkd(pd.DataFrame({"BTC": 0.5 * sig, "ETH": 0.5 * sig}), ["BTC", "ETH"])
# B leverage crowding
w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    oi = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last().reindex(days)
    f = B.funding(c).copy(); f.index = (f.index - pd.Timedelta(seconds=1)).floor("D"); fm = f.groupby(level=0).mean().reindex(days).rolling(7).mean()
    ev = ((oi / oi.shift(7) - 1 > 0.15) & (fm > 0.0003)).astype(float)
    w[c] = -0.5 * ev.rolling(3, min_periods=1).max()
S["B leverage crowding"] = mkd(w.fillna(0.0), ["BTC", "ETH"])
# C weekend reversal XS
coins = CS._breadth_universe(); H = CS._breadth_close(coins); P = H.resample("1D").last(); listed = P.notna().cumsum() >= 60
vol = P.pct_change(fill_method=None).rolling(30).std()
wk = pd.DataFrame(0.0, index=P.index, columns=coins)
for d in P.index[P.index.weekday == 0]:                                    # Monday 00:00 close row = Sunday's daily bar closes at Mon 00:00
    fri = d - pd.Timedelta(days=3)
    if fri not in P.index:
        continue
    ret = (P.loc[d - pd.Timedelta(days=1)] / P.loc[fri - pd.Timedelta(days=1)] - 1).where(listed.loc[d - pd.Timedelta(days=1)])
    rk = (-ret).rank(pct=True); iv = 1 / vol.loc[d - pd.Timedelta(days=1)]
    wl, ws = iv.where(rk > 2 / 3, 0.0).fillna(0.0), iv.where(rk <= 1 / 3, 0.0).fillna(0.0)
    if wl.sum() == 0 or ws.sum() == 0:
        continue
    row = wl / wl.sum() - ws / ws.sum()
    for k in range(4):                                                      # rows Sun..Wed (decided at the close of d-1+k) -> held Mon..Thu
        wk.loc[d - pd.Timedelta(days=1) + pd.Timedelta(days=k)] = row.to_numpy()
S["C weekend reversal XS"] = CS.premium_carry_breadth(coins=coins, w=wk).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
# D US-open seasonality
hc = B.panel("close", "1h", ["BTC", "ETH"]).loc[:END + " 23:00"]; rr = hc.pct_change(fill_method=None).fillna(0.0)
pos = pd.DataFrame(0.0, index=hc.index, columns=hc.columns); m = (hc.index.weekday < 5) & np.isin(hc.index.hour, [13, 14]); pos[m] = -0.5
fh = B.funding_panel(["BTC", "ETH"]); fh.index = fh.index - pd.Timedelta(hours=1); fh = fh.groupby(level=0).sum().reindex(hc.index).fillna(0.0)
S["D US-open seasonality"] = ((pos * rr).sum(axis=1) - (pos * fh).sum(axis=1) - pos.diff().abs().fillna(0.0).sum(axis=1) * 5 / 1e4).reindex(L.H6.index).fillna(0.0)
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {}
for nm, h in S.items():
    s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6 2022-26": round(c, 3), "orthogonal candidate": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2)}
    print(nm, out[nm], flush=True)
pd.DataFrame(S).to_parquet(ROOT / "results/gen345_sleeves.parquet")
json.dump(out, open(ROOT / "results/gen345.json", "w"), indent=1)
