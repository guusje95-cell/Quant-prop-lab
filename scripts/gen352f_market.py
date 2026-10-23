"""Gen352f (config/gen352b_protocol.json): crash buys executed as market orders on 5-minute closes, heavy costs, latency. Writes results/gen352f.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen352b_verify.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\ndef run(")[0], "gen352b", "exec"), g)
for k in ("L", "coins", "idx", "n", "END", "ROOT", "C", "sd", "fh", "K5", "pk"):
    globals()[k] = g[k]


def run(delay=0, ein=20e-4, eout=10e-4):
    ev = []
    for c in pk:
        j = coins.index(c); k5 = K5[c]; k5 = k5[~k5.index.duplicated()]; hr = k5.index.floor("h")
        lim = pd.Series(C[:-0 or None, j], index=idx).shift(1) * (1 - 3 * pd.Series(sd[:, j], index=idx))
        lv = lim.reindex(hr).to_numpy(); below = (k5.to_numpy() <= lv) & np.isfinite(lv)
        first = pd.Series(below, index=k5.index).groupby(hr).idxmax()[pd.Series(below, index=k5.index).groupby(hr).any()]
        for h_, ts in first.items():
            t = idx.get_indexer([h_])[0]
            if t < 0:
                continue
            pos = k5.index.get_loc(ts) + delay
            if pos >= len(k5) or k5.index[pos].floor("h") != h_:
                continue
            ev.append((t, j, float(k5.iloc[pos])))
    ev.sort(); ends = []; p = np.zeros(n)
    for t, j, px in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5 or t + 4 >= n:
            continue
        ends.append(t + 4); p[t] += 0.1 * (C[t, j] / px - 1) - 0.1 * ein
        for q in range(t + 1, t + 5):
            p[q] += 0.1 * (C[q, j] / C[q - 1, j] - 1) - 0.1 * fh[q, j]
        p[t + 4] -= 0.1 * eout
    return pd.Series(p, index=idx), len(ev)


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
out = {}
for nm, kw in (("market at the first 5-min close below, 20/10 bp", {}), ("latency: next 5-min close, 20/10 bp", dict(delay=1)),
               ("market, 30/15 bp", dict(ein=30e-4, eout=15e-4)), ("latency 10 min, 20/10 bp", dict(delay=2))):
    h, k = run(**kw); out[nm] = {"D/T/H": per(h), "signals": k}; print(nm, out[nm], flush=True)
    if nm.startswith("market at"):
        base = h
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); d = base.groupby(base.index.floor("D")).sum()
out["corr v8.6"] = round(float(pd.concat([d, vd], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
out["by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
b = L.book([base.reindex(L.H6.index).fillna(0.0).rename("crash buys")]); kk = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
Rf = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
out["v8.6 + sleeve"] = {"D/T/H": kk, "strict pass": bool(all(a >= q for a, q in zip(kk[1:], Rf[1:])) and kk[0] >= Rf[0] + 0.05)}
out["VERDICT tradable"] = bool(all(x >= 0.8 for x in out["market at the first 5-min close below, 20/10 bp"]["D/T/H"]) and all(x >= 0.5 for x in out["latency: next 5-min close, 20/10 bp"]["D/T/H"]))
print(json.dumps({k: out[k] for k in ("corr v8.6", "by year", "v8.6 + sleeve", "VERDICT tradable")}))
json.dump(out, open(ROOT / "results/gen352f.json", "w"), indent=1); base.to_frame("crash buys").to_parquet(ROOT / "results/gen352f_series.parquet")
