"""Gen353 (config/gen353_protocol.json): spot-volume surges, BTC-shock laggards, hourly premium rank. Writes results/gen353.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, coins, Hc, idx, n, pnl, zz, pk, END, ROOT, R = (g[k] for k in ("L", "B", "X", "coins", "Hc", "idx", "n", "pnl", "zz", "pk", "END", "ROOT", "R"))
S = {}
P = np.zeros((n, len(coins)))
for c in pk:
    sp = pd.read_parquet(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet"); sp.index = pd.DatetimeIndex(sp.index); sp = sp[~sp.index.duplicated()].reindex(idx)
    pq = B.k5(c)["quote_volume"].resample("1h").sum().reindex(idx)
    z = np.nan_to_num(zz(np.log(sp["quote_volume"] / pq.replace(0, np.nan)))); r = np.nan_to_num(sp["close"].pct_change(fill_method=None).to_numpy()); j = coins.index(c)
    for t in np.flatnonzero(z > 3):
        P[t + 1:min(t + 5, n), j] = 0.1 * np.sign(r[t])
S["A spot-volume surge"] = pd.DataFrame(P, index=idx, columns=coins)
Rv = Hc.pct_change(fill_method=None); zb = np.nan_to_num(zz(Rv["BTC"])); P = np.zeros((n, len(coins))); others = [c for c in coins if c != "BTC"]
for t in np.flatnonzero(np.abs(zb) > 3):
    r = Rv.iloc[t][others].dropna()
    if len(r) < 9:
        continue
    if zb[t] < 0:
        lag = r.sort_values(ascending=False).index[:len(r) // 3]; s = -0.05
    else:
        lag = r.sort_values().index[:len(r) // 3]; s = 0.05
    for c in lag:
        P[t + 1:min(t + 4, n), coins.index(c)] = s
S["B BTC-shock laggards"] = pd.DataFrame(P, index=idx, columns=coins)
Zp = {}
for c in coins:
    p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); Zp[c] = zz(p.reindex(idx))
Zp = pd.DataFrame(Zp, index=idx); vol = Rv.rolling(720, min_periods=500).std().shift(1)
W = pd.DataFrame(np.nan, index=idx, columns=coins); reb = idx[idx.hour % 8 == 7]
rk = Zp.loc[reb].rank(axis=1, pct=True); iv = (1 / vol.loc[reb]).where(Zp.loc[reb].notna())
wl, ws = iv.where(rk <= 1 / 3, 0.0), iv.where(rk > 2 / 3, 0.0)
W.loc[reb] = (wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)).fillna(0.0).to_numpy()
S["C hourly premium rank"] = W.ffill().shift(1).fillna(0.0) * 0.5
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm, Pm in S.items():
    h = pnl(Pm).reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "gross": [round(x, 3) for x in L.per(pnl(Pm, 0.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")],
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen353_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen353.json", "w"), indent=1)
