"""Gen352d (config/gen352b_protocol.json): crash limit buys entirely on OKX data; parameter neighbourhood. Writes results/gen352d.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen352b_verify.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\ndef run(")[0], "gen352b", "exec"), g)
for k in ("L", "B", "coins", "Hc", "idx", "n", "pk", "END", "ROOT", "C", "Lw", "sd", "fh", "R"):
    globals()[k] = g[k]


def engine(Cm, Lm, sdm, k=3.0, hold=4):
    ev = []
    for j in range(Cm.shape[1]):
        for t in np.flatnonzero(np.isfinite(sdm[:, j])):
            if t == 0 or not np.isfinite(Cm[t - 1, j]):
                continue
            lim = Cm[t - 1, j] * (1 - k * sdm[t, j])
            if np.isfinite(Lm[t, j]) and Lm[t, j] <= lim * (1 - 2e-4):
                ev.append((t, j, lim))
    ev.sort(); ends = []; p = np.zeros(n)
    for t, j, px in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5 or t + hold >= n:
            continue
        ends.append(t + hold); p[t] += 0.1 * (Cm[t, j] / px - 1) - 0.1 * 2e-4
        for q in range(t + 1, t + 1 + hold):
            p[q] += 0.1 * (Cm[q, j] / Cm[q - 1, j] - 1) - 0.1 * fh[q, j]
        p[t + hold] -= 0.1 * 5e-4
    return pd.Series(p, index=idx), len(ev)


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; oc, ol = {}, {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()].reindex(idx); oc[c] = x["close"]; ol[c] = x["low"]
OC = pd.DataFrame(oc).reindex(columns=coins); OL = pd.DataFrame(ol).reindex(columns=coins)
osd = OC.pct_change(fill_method=None).rolling(720, min_periods=500).std().shift(1).to_numpy()
out = {}
h, k = engine(OC.to_numpy(), OL.to_numpy(), osd); out["R1 OKX only"] = {"D/T/H": per(h), "fills": k}; print(out["R1 OKX only"], flush=True)
grid = {}
for kk in (2.5, 3.0, 3.5):
    for hd in (2, 4, 8):
        h, _ = engine(C, Lw, sd, kk, hd); grid[f"k {kk} hold {hd}"] = per(h); print(kk, hd, grid[f"k {kk} hold {hd}"], flush=True)
out["neighbourhood"] = grid; med = np.median(np.array(list(grid.values())), axis=0); out["neighbourhood median"] = np.round(med, 3).tolist()
out["VERDICT replicated"] = bool(all(x >= 1.0 for x in out["R1 OKX only"]["D/T/H"]) and all(x >= 1.5 for x in med))
print(out["neighbourhood median"], out["VERDICT replicated"])
json.dump(out, open(ROOT / "results/gen352d.json", "w"), indent=1)
