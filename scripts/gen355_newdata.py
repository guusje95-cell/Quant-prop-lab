"""Gen355 (config/gen355_protocol.json): cross-venue funding spread XS, retail positioning XS, extreme negative funding. Writes results/gen355.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, CS, coins, Hc, idx, n, pnl, pk, END, ROOT = (g[k] for k in ("L", "B", "X", "CS", "coins", "Hc", "idx", "n", "pnl", "pk", "END", "ROOT"))
P = Hc.resample("1D").last(); listed = P.notna().cumsum() >= 60; vol = P.pct_change(fill_method=None).rolling(30).std()


def xs_w(score, hold, uni=None):
    sc = score.where(listed) if uni is None else score[uni].where(listed[uni])
    rk = sc.rank(axis=1, pct=True); iv = (1 / vol[sc.columns]).where(sc.notna())
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = (wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)).fillna(0.0).reindex(columns=coins).fillna(0.0)
    return CS._hold(w, hold, True)


fb_ = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fbd = fb_.copy(); fbd.index = (fbd.index - pd.Timedelta(seconds=1)).floor("D"); fbd = fbd.groupby(level=0).sum().reindex(P.index)
by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); sym = dict(zip(by.coin, by.symbol)); yb = {}
for c in coins:
    f = ROOT / f"research_data/bybit/funding/{sym.get(c, '')}.parquet"
    if c in sym and f.exists():
        x = pd.read_parquet(f)["funding_rate"]; x.index = (pd.DatetimeIndex(x.index) - pd.Timedelta(seconds=1)).floor("D"); yb[c] = x.groupby(level=0).sum()
YB = pd.DataFrame(yb).reindex(index=P.index, columns=coins)
spread = YB.rolling(7, min_periods=5).mean() - fbd.rolling(7, min_periods=5).mean()
S = {"A cross-venue funding spread XS": CS.premium_carry_breadth(coins=coins, w=xs_w(-spread, 7))}
ls = pd.DataFrame({c: B.metrics(c)["count_long_short_ratio"].resample("1D").mean() for c in pk}).reindex(P.index)
zl = (ls - ls.rolling(90, min_periods=60).mean()) / ls.rolling(90, min_periods=60).std()
S["B retail positioning contrarian XS"] = CS.premium_carry_breadth(coins=coins, w=xs_w(-zl.reindex(columns=coins), 3, uni=pk))
ev = []
for j, c in enumerate(coins):
    f = fb_[c].dropna()
    for ts in f.index[f < -0.001]:
        t = idx.get_indexer([ts.floor("h")])[0]
        if t >= 0:
            ev.append((t, j))
ev.sort(); Pm = np.zeros((n, len(coins))); ends = []
for t, j in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5 or t + 1 >= n:
        continue
    Pm[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
S["C extreme negative funding"] = pnl(pd.DataFrame(Pm, index=idx, columns=coins))
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {"C events": len(ev)}
for nm, h in S.items():
    h = h.loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0); first = str(h.ne(0).idxmax().date())
    s = [round(x, 3) for x in L.per(h, max(first, "2020-01-01"))]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"first": first, "sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen355_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen355.json", "w"), indent=1)
