"""Gen352e (descriptive, registered in config/gen352b_protocol.json notes): where the crash-limit-buy P&L comes from - the fill hour
(limit -> close) vs the 4 h after; and the version that enters only at the CLOSE of the hour whose low hit the level (market order).
Writes results/gen352e.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen352b_verify.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\ndef run(")[0], "gen352b", "exec"), g)
for k in ("L", "coins", "idx", "n", "END", "ROOT", "C", "Lw", "sd", "fh"):
    globals()[k] = g[k]
ev = []
for j in range(len(coins)):
    for t in np.flatnonzero(np.isfinite(sd[:, j])):
        if t and np.isfinite(C[t - 1, j]):
            lim = C[t - 1, j] * (1 - 3 * sd[t, j])
            if np.isfinite(Lw[t, j]) and Lw[t, j] <= lim * (1 - 2e-4):
                ev.append((t, j, lim))
ev.sort(); ends = []; fill = np.zeros(n); after = np.zeros(n); atclose = np.zeros(n)
for t, j, px in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5 or t + 5 >= n:
        continue
    ends.append(t + 4); fill[t] += 0.1 * (C[t, j] / px - 1) - 0.1 * 2e-4
    for q in range(t + 1, t + 5):
        after[q] += 0.1 * (C[q, j] / C[q - 1, j] - 1) - 0.1 * fh[q, j]
    after[t + 4] -= 0.1 * 5e-4
    atclose[t] -= 0.1 * 5e-4                                               # market buy at the fill hour's close (taker both ways)
    for q in range(t + 1, t + 5):
        atclose[q] += 0.1 * (C[q, j] / C[q - 1, j] - 1) - 0.1 * fh[q, j]
    atclose[t + 4] -= 0.1 * 5e-4
per = lambda a: [round(x, 3) for x in L.per(pd.Series(a, index=idx).reindex(L.H6.index).fillna(0.0), "2020-01-01")]
out = {"share of P&L from the fill hour": round(float(fill.sum() / (fill.sum() + after.sum())), 3),
       "fill hour only D/T/H": per(fill), "the 4 h after only D/T/H": per(after), "enter at the fill hour's close (market) D/T/H": per(atclose),
       "mean fill-hour gain per fill (bp)": round(float(fill.sum() / max(1, (fill != 0).sum()) / 0.1 * 1e4), 1)}
print(json.dumps(out, indent=0)); json.dump(out, open(ROOT / "results/gen352e.json", "w"), indent=1)
