"""Gen356 (config/gen356_protocol.json): OKX / Coinbase volume share XS, euro premium spikes. Writes results/gen356.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen355_newdata.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nfb_ = pd.concat")[0], "gen355", "exec"), g)
L, B, X, CS, coins, Hc, idx, n, pnl, pk, END, ROOT, P, xs_w = (g[k] for k in ("L", "B", "X", "CS", "coins", "Hc", "idx", "n", "pnl", "pk", "END", "ROOT", "P", "xs_w")); zz = g["g"]["zz"]
rd = lambda f: (lambda x: x[~x.index.duplicated()].sort_index())(pd.read_parquet(f).pipe(lambda x: x.set_axis(pd.DatetimeIndex(x.index))))
bq = pd.concat([B.panel("quote_volume", "1D", pk)] + [rd(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["quote_volume"].resample("1D").sum().rename(c)
                                                    for c in coins if c not in pk], axis=1).reindex(P.index)[coins]
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; oq = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        oq[c] = rd(f)["volQuote"].resample("1D").sum()
OQ = pd.DataFrame(oq).reindex(index=P.index, columns=coins)
sh = (OQ / (OQ + bq)).replace(0, np.nan); scA = np.log(sh.rolling(7, min_periods=5).mean() / sh.rolling(90, min_periods=60).mean())
S = {"A OKX volume share XS": CS.premium_carry_breadth(coins=coins, w=xs_w(scA, 3))}
cq = {}
for c in coins:
    f = ROOT / f"research_data/coinbase/{c}-USD_1h.parquet"
    if f.exists():
        x = rd(f); cq[c] = (x["volume"] * x["close"]).resample("1D").sum()
CQ = pd.DataFrame(cq).reindex(P.index); cbs = list(CQ.columns)
s2 = (CQ / bq[cbs]).replace(0, np.nan); scB = np.log(s2.rolling(7, min_periods=5).mean() / s2.rolling(90, min_periods=60).mean())
S["B Coinbase volume share XS"] = CS.premium_carry_breadth(coins=coins, w=xs_w(scB.reindex(columns=coins), 3, uni=cbs))
be = rd(ROOT / "research_data/binance_fiat/BTCEUR_1h.parquet")["close"].reindex(idx); eu = rd(ROOT / "research_data/binance_fiat/EURUSDT_1h.parquet")["close"].reindex(idx)
z = np.nan_to_num(zz(be / (eu * Hc["BTC"]) - 1)); Pm = np.zeros((n, len(coins)))
for t in np.flatnonzero(np.abs(z) > 3):
    for c in ("BTC", "ETH"):
        Pm[t + 1:min(t + 5, n), coins.index(c)] = 0.25 * np.sign(z[t])
S["C euro premium hourly spike"] = pnl(pd.DataFrame(Pm, index=idx, columns=coins))
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm, h in S.items():
    h = h.loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0); first = str(h.ne(0).idxmax().date())
    s = [round(x, 3) for x in L.per(h, max(first, "2020-01-01"))]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"first": first, "sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen356_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen356.json", "w"), indent=1)
