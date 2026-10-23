"""Gen355b (config/gen355b_protocol.json): robustness of the extreme-negative-funding long. Writes results/gen355b.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, coins, Hc, idx, n, pk, END, ROOT, R, fund = (g[k] for k in ("L", "B", "X", "coins", "Hc", "idx", "n", "pk", "END", "ROOT", "R", "fund"))
fb_ = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); sym = dict(zip(by.coin, by.symbol))
spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
bcost = pd.Series({c: 5.5 + 0.5 * float(spr.get(sym.get(c, ""), spr.median())) for c in coins})
yb = {}
for c in coins:
    f = ROOT / f"research_data/bybit/funding/{sym.get(c, '')}.parquet"
    if c in sym and f.exists():
        x = pd.read_parquet(f)["funding_rate"]; x.index = pd.DatetimeIndex(x.index); yb[c] = x[~x.index.duplicated()]
YBraw = pd.DataFrame(yb).reindex(columns=coins)
FBy = YBraw.copy(); FBy.index = FBy.index - pd.Timedelta(hours=1); FBy = FBy.groupby(level=0).sum().reindex(idx).fillna(0.0)
FBmix = fund.copy()
for c in yb:
    st = yb[c].index.min(); FBmix.loc[st:, c] = FBy.loc[st:, c]


def positions(src, th=-0.001, hold=24, lag=0):
    ev = []
    for j, c in enumerate(coins):
        if c not in src:
            continue
        f = src[c].dropna()
        for ts in f.index[f < th]:
            t = idx.get_indexer([ts.floor("h")])[0]
            if t >= 0:
                ev.append((t + lag, j))
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5 or t >= n:
            continue
        P[t:min(t + hold, n), j] = 0.1; ends.append(t + hold)
    return pd.DataFrame(P, index=idx, columns=coins), len(ev)


def pnl(P, cost=5.0, fin=None, ret=None, part="all"):
    fin = fund if fin is None else fin; ret = R if ret is None else ret; d = P.diff().abs().fillna(0.0)
    price = (P * ret).sum(axis=1); fnd = -(P * fin).sum(axis=1); c = (d * cost).sum(axis=1) / 1e4
    return {"all": price + fnd - c, "price": price - c, "funding": fnd}[part]


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
P0, ne = positions(fb_); out = {"base (Gen355 C)": per(pnl(P0)), "events": ne}
out["1 Bybit costs + Bybit funding"] = per(pnl(P0, bcost, FBmix))
Py, ney = positions(YBraw); out["2 Bybit signal (Bybit costs + funding)"] = per(pnl(Py, bcost, FBmix)); out["2 Bybit events"] = ney
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; ro = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()]; ro[c] = x.reindex(idx).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=coins); Pm = P0.where(RO.notna(), 0.0)
out["3 same cells Binance / OKX"] = [per(pnl(Pm)), per(pnl(Pm, ret=RO.fillna(0.0)))]
grid = {f"th {th:.2%} hold {hd}": per(pnl(positions(fb_, th, hd)[0])) for th in (-0.0005, -0.001, -0.0015) for hd in (12, 24, 48)}
out["4 neighbourhood"] = grid; out["4 median"] = np.round(np.median(np.array(list(grid.values())), axis=0), 3).tolist()
out["5 one hour later"] = per(pnl(positions(fb_, lag=1)[0]))
out["6 price part / funding part"] = [per(pnl(P0, part="price")), per(pnl(P0, part="funding"))]
h = pnl(P0); d = h.groupby(h.index.floor("D")).sum()
out["7 by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
cs = L.H6[["cascade limit strict", "delev bounce"]].groupby(L.H6.index.floor("D")).sum()
sp = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]; sp = sp.groupby(sp.index.floor("D")).sum()
out["7 corr cascade / delev / premium spike"] = [round(float(pd.concat([x, d], axis=1).loc["2020":END].corr().iloc[0, 1]), 3) for x in (cs.iloc[:, 0], cs.iloc[:, 1], sp)]
ok = (all(x >= 0.4 for x in out["1 Bybit costs + Bybit funding"]) and all(x >= 0.4 for x in out["2 Bybit signal (Bybit costs + funding)"])
      and all(x > 0.3 for x in out["4 median"]) and all(x > 0 for x in out["6 price part / funding part"][0])
      and all(np.sign(a) == np.sign(b) for a, b in zip(*out["3 same cells Binance / OKX"])))
out["CANDIDATE"] = bool(ok)
print(json.dumps(out, indent=0)); json.dump(out, open(ROOT / "results/gen355b.json", "w"), indent=1)
h.to_frame("negative funding long").to_parquet(ROOT / "results/gen355_negfunding.parquet")
