"""Gen352b (config/gen352b_protocol.json): verification of the crash limit buys. Writes results/gen352b.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, coins, Hc, idx, n, pnl, zz, pk, END, ROOT, R, fund = (g[k] for k in ("L", "B", "X", "coins", "Hc", "idx", "n", "pnl", "zz", "pk", "END", "ROOT", "R", "fund"))
LO = pd.concat([B.panel("low", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in coins if c not in pk], axis=1)
LO = LO[~LO.index.duplicated()]; LO.index = pd.DatetimeIndex(LO.index); LO = LO.reindex(idx)[coins]
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; OKL = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()].reindex(idx)
        OKL[c] = (x["low"] * (1000 if c.startswith("1000") else 1)).to_numpy()   # OKX PEPE/SHIB are per coin; Binance 1000x
# 5-minute first close below the limit (pack coins)
K5 = {c: B.k5(c)["close"] for c in pk}
C = Hc.to_numpy(); Lw = LO.to_numpy(); sd = R.where(Hc.notna()).rolling(720, min_periods=500).std().shift(1).to_numpy(); fh = fund.to_numpy()
by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); sym = dict(zip(by.coin, by.symbol))
spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
bcost = np.array([5.5 + 0.5 * float(spr.get(sym.get(c, ""), spr.median())) for c in coins]) / 1e4


def run(through=2e-4, okx=False, five=False, maker=2e-4, exit_cost=None, coin_set=None):
    ev = []
    for j, c in enumerate(coins):
        if coin_set is not None and c not in coin_set:
            continue
        for t in np.flatnonzero(np.isfinite(sd[:, j])):
            if t == 0 or not np.isfinite(C[t - 1, j]):
                continue
            lim = C[t - 1, j] * (1 - 3 * sd[t, j])
            if not (np.isfinite(Lw[t, j]) and Lw[t, j] <= lim * (1 - through)):
                continue
            if okx and not (c in OKL and np.isfinite(OKL[c][t]) and OKL[c][t] <= lim * (1 - through)):
                continue
            px = lim
            if five:
                k = K5[c].loc[idx[t]:idx[t] + pd.Timedelta(minutes=55)]; below = k[k <= lim]
                if below.empty:
                    continue
                px = float(below.iloc[0])
            ev.append((t, j, px))
    ev.sort(); ends = []; p = np.zeros(n)
    for t, j, px in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5 or t + 4 >= n:
            continue
        ends.append(t + 4); p[t] += 0.1 * (C[t, j] / px - 1) - 0.1 * maker
        for k in range(t + 1, t + 5):
            p[k] += 0.1 * (C[k, j] / C[k - 1, j] - 1) - 0.1 * fh[k, j]
        p[t + 4] -= 0.1 * (exit_cost[j] if exit_cost is not None else 5e-4)
    return pd.Series(p, index=idx), len(ev)


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
out = {}
for nm, kw in (("base (Gen352 A)", {}), ("1 trade-through 20 bp", dict(through=2e-3)), ("2 OKX low confirms", dict(okx=True)),
               ("2b same coins without the OKX filter", dict(coin_set=set(OKL))), ("3 5-minute close below (pack coins)", dict(five=True, coin_set=set(pk))),
               ("3b pack coins, wick fill", dict(coin_set=set(pk))), ("4 costs x2", dict(maker=4e-4, exit_cost=np.full(len(coins), 1e-3))),
               ("5 Bybit exit cost", dict(exit_cost=bcost))):
    h, k = run(**kw); out[nm] = {"D/T/H": per(h), "fills": k}; print(nm, out[nm], flush=True)
    if nm == "base (Gen352 A)":
        base = h
d = base.groupby(base.index.floor("D")).sum()
out["7 by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
cs = L.H6[["cascade limit strict", "delev bounce"]].groupby(L.H6.index.floor("D")).sum()
out["7 corr cascade / delev"] = [round(float(pd.concat([cs.iloc[:, i], d], axis=1).loc["2020":END].corr().iloc[0, 1]), 3) for i in range(2)]
b = L.book([base.reindex(L.H6.index).fillna(0.0).rename("crash limit buys")]); k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
Rf = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
out["6 v8.6 + sleeve"] = {"D/T/H": k, "reference": Rf, "strict pass": bool(all(a >= q for a, q in zip(k[1:], Rf[1:])) and k[0] >= Rf[0] + 0.05)}
okx_ok = all(x >= 1.0 for x in out["2 OKX low confirms"]["D/T/H"]); five_ok = all(x >= 1.0 for x in out["3 5-minute close below (pack coins)"]["D/T/H"])
out["VERDICT real edge (2 and 3 >= 1.0 every period)"] = bool(okx_ok and five_ok)
print(json.dumps({k: out[k] for k in ("7 by year", "7 corr cascade / delev", "6 v8.6 + sleeve", "VERDICT real edge (2 and 3 >= 1.0 every period)")}), flush=True)
json.dump(out, open(ROOT / "results/gen352b.json", "w"), indent=1)
