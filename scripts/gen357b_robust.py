"""Gen357b (config/gen357b_protocol.json): robustness of the daily crash reversal. Writes results/gen357b.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen357_intraday.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS[\"B volume-shock")[0], "gen357", "exec"), g)
L, coins, Hc, idx, n, pnl, END, ROOT, D, dr, R = (g[k] for k in ("L", "coins", "Hc", "idx", "n", "pnl", "END", "ROOT", "D", "dr", "R")); fund = g["g"]["fund"]
h2 = _src  # noqa


def positions(k=3.0, hold=3, lag=0):
    sdd = dr.rolling(90, min_periods=60).std().shift(1); mask = dr < -k * sdd
    ev = []
    for j, c in enumerate(coins):
        for d in mask.index[mask[c].fillna(False).to_numpy()]:
            ev.append((d, j))
    ev.sort(); Pd = np.zeros((len(D), len(coins))); ends = []; di = {d: i for i, d in enumerate(D.index)}
    for d, j in ev:
        i = di[d]; ends = [e for e in ends if e > i]
        if len(ends) >= 8:
            continue
        Pd[i:i + hold, j] = 0.1; ends.append(i + hold)
    w = pd.DataFrame(Pd, index=D.index, columns=coins)
    held = w.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
    return held.shift(lag).fillna(0.0), len(ev)


by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); sym = dict(zip(by.coin, by.symbol))
spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
bcost = pd.Series({c: 5.5 + 0.5 * float(spr.get(sym.get(c, ""), spr.median())) for c in coins})
FB = fund.copy()
for c in coins:
    f = ROOT / f"research_data/bybit/funding/{sym.get(c, '')}.parquet"
    if c in sym and f.exists():
        x = pd.read_parquet(f)["funding_rate"]; x.index = pd.DatetimeIndex(x.index) - pd.Timedelta(hours=1); x = x.groupby(level=0).sum()
        FB.loc[x.index.min():, c] = x.reindex(idx).loc[x.index.min():].fillna(0.0)


def P_L(P, cost=5.0, fin=None, ret=None):
    fin = fund if fin is None else fin; ret = R if ret is None else ret
    return (P * ret).sum(axis=1) - (P * fin).sum(axis=1) - (P.diff().abs().fillna(0.0) * cost).sum(axis=1) / 1e4


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
P0, ne = positions(); out = {"base (Gen357 C)": per(P_L(P0)), "events": ne, "1 Bybit costs + funding": per(P_L(P0, bcost, FB))}
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; ro = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()]; ro[c] = x.reindex(idx).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=coins); Pm = P0.where(RO.notna(), 0.0)
out["2 same cells Binance / OKX"] = [per(P_L(Pm)), per(P_L(Pm, ret=RO.fillna(0.0)))]
grid = {f"k {k} hold {hd}": per(P_L(positions(k, hd)[0])) for k in (2.5, 3.0, 3.5) for hd in (2, 3, 5)}
out["3 neighbourhood"] = grid; med = np.median(np.array(list(grid.values())), axis=0); out["3 median"] = np.round(med, 3).tolist()
out["4 one hour later"] = per(P_L(positions(lag=1)[0]))
h = P_L(P0); d = h.groupby(h.index.floor("D")).sum()
out["5 by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
oth = {"delev bounce": L.H6["delev bounce"], "cascade": L.H6["cascade limit strict"],
       "premium spike": pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"],
       "negative funding": pd.read_parquet(ROOT / "results/gen355_negfunding.parquet").iloc[:, 0]}
out["5 corr"] = {k: round(float(pd.concat([v.groupby(v.index.floor("D")).sum(), d], axis=1).loc["2020":END].corr().iloc[0, 1]), 3) for k, v in oth.items()}
b1 = out["1 Bybit costs + funding"]; ok_years = sum(v > 0 for v in out["5 by year"].values())
out["CANDIDATE"] = bool(b1[0] > 0 and b1[1] >= 0.5 and b1[2] >= 0.5 and all(x > 0 for x in med) and med[1] >= 0.5 and med[2] >= 0.5
                        and all(np.sign(a) == np.sign(b) for a, b in zip(*out["2 same cells Binance / OKX"])) and ok_years >= 5)
print(json.dumps(out, indent=0)); json.dump(out, open(ROOT / "results/gen357b.json", "w"), indent=1)
h.to_frame("daily crash reversal").to_parquet(ROOT / "results/gen357_crashrev.parquet")
