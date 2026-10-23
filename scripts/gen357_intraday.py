"""Gen357 (config/gen357_protocol.json): intraday momentum, volume-shock momentum, daily crash reversal. Writes results/gen357.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, CS, coins, Hc, idx, n, pnl, pk, END, ROOT, R = (g[k] for k in ("L", "B", "X", "CS", "coins", "Hc", "idx", "n", "pnl", "pk", "END", "ROOT", "R"))
S = {}
Pm = pd.DataFrame(0.0, index=idx, columns=coins); Rv = Hc.pct_change(fill_method=None)
for c in ("BTC", "ETH"):
    first = Rv[c][idx.hour == 0]; first.index = first.index.floor("D")
    sgn = np.sign(first).reindex(idx.floor("D")).set_axis(idx)
    Pm.loc[idx.hour == 23, c] = 0.5 * sgn[idx.hour == 23].fillna(0.0)
S["A intraday momentum"] = Pm
D = Hc.resample("1D").last(); dr = D.pct_change(fill_method=None)
rd = lambda f: (lambda x: x[~x.index.duplicated()].sort_index())(pd.read_parquet(f).pipe(lambda x: x.set_axis(pd.DatetimeIndex(x.index))))
qv = pd.concat([B.panel("quote_volume", "1D", pk)] + [rd(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["quote_volume"].resample("1D").sum().rename(c)
                                                    for c in coins if c not in pk], axis=1).reindex(D.index)[coins]
lq = np.log(qv.replace(0, np.nan)); zq = (lq - lq.rolling(90, min_periods=60).mean().shift(1)) / lq.rolling(90, min_periods=60).std().shift(1)
sdd = dr.rolling(90, min_periods=60).std().shift(1)


def daily_events(mask, sign):
    ev = []
    for j, c in enumerate(coins):
        for d in mask.index[mask[c].fillna(False).to_numpy()]:
            ev.append((d, j, float(sign.loc[d, c])))
    ev.sort(); Pd = np.zeros((len(D), len(coins))); ends = []; di = {d: i for i, d in enumerate(D.index)}
    for d, j, s in ev:
        i = di[d]; ends = [e for e in ends if e > i]
        if len(ends) >= 8 or s == 0:
            continue
        Pd[i:i + 3, j] = 0.1 * s; ends.append(i + 3)                   # row d = decided at d's close, held d+1..d+3
    w = pd.DataFrame(Pd, index=D.index, columns=coins)
    held = w.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
    return held


S["B volume-shock momentum"] = daily_events(zq > 3, np.sign(dr))
S["C daily crash reversal"] = daily_events(dr < -3 * sdd, pd.DataFrame(1.0, index=D.index, columns=coins))
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm, Pm in S.items():
    h = pnl(Pm).reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "gross": [round(x, 3) for x in L.per(pnl(Pm, 0.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")],
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen357_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen357.json", "w"), indent=1)
