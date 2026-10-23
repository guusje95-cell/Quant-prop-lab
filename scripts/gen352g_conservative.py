"""Gen352g (descriptive, the most conservative resting-limit version): fill only if BOTH the Binance and the OKX hourly low trade
20 bp through the limit; size capped at 1% of the hour's volume; Bybit exit cost; in v8.6. Writes results/gen352g.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen352c_capacity.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\ndef run(")[0], "gen352c", "exec"), g)
for k in ("L", "coins", "idx", "n", "END", "ROOT", "C", "Lw", "sd", "fh", "OKL", "QV", "USD"):
    globals()[k] = g[k]
bcost = g["g"]["bcost"]
ev = []
for j, c in enumerate(coins):
    if c not in OKL:
        continue
    for t in np.flatnonzero(np.isfinite(sd[:, j])):
        if t and np.isfinite(C[t - 1, j]):
            lim = C[t - 1, j] * (1 - 3 * sd[t, j])
            if np.isfinite(Lw[t, j]) and Lw[t, j] <= lim * (1 - 2e-3) and np.isfinite(OKL[c][t]) and OKL[c][t] <= lim * (1 - 2e-3):
                s = min(0.1, 0.01 * np.nan_to_num(QV[t, j]) / USD)
                if s > 0:
                    ev.append((t, j, lim, s))
ev.sort(); ends = []; p = np.zeros(n)
for t, j, px, s in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5 or t + 4 >= n:
        continue
    ends.append(t + 4); p[t] += s * (C[t, j] / px - 1) - s * 2e-4
    for q in range(t + 1, t + 5):
        p[q] += s * (C[q, j] / C[q - 1, j] - 1) - s * fh[q, j]
    p[t + 4] -= s * bcost[j]
h = pd.Series(p, index=idx).reindex(L.H6.index).fillna(0.0)
out = {"conservative D/T/H": [round(x, 3) for x in L.per(h, "2020-01-01")], "fills": len(ev)}
d = h.groupby(h.index.floor("D")).sum(); vd = L.V7.groupby(L.V7.index.floor("D")).sum()
out["corr v8.6"] = round(float(pd.concat([d, vd], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
out["by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
b = L.book([h.rename("crash limit buys")]); kk = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
Rf = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
out["v8.6 + sleeve"] = {"D/T/H": kk, "strict pass": bool(all(a >= q for a, q in zip(kk[1:], Rf[1:])) and kk[0] >= Rf[0] + 0.05)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen352g.json", "w"), indent=1); h.to_frame("crash limit buys").to_parquet(ROOT / "results/gen352g_series.parquet")
