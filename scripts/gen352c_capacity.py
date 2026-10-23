"""Gen352c (config/gen352b_protocol.json): crash limit buys with fills capped at a share of the hour's traded volume. Writes results/gen352c.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen352b_verify.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\ndef run(")[0], "gen352b", "exec"), g)
for k in ("L", "B", "coins", "Hc", "idx", "n", "pk", "END", "ROOT", "C", "Lw", "sd", "fh", "OKL", "K5"):
    globals()[k] = g[k]
QV = pd.concat([B.panel("quote_volume", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["quote_volume"].rename(c) for c in coins if c not in pk], axis=1)
QV = QV[~QV.index.duplicated()]; QV.index = pd.DatetimeIndex(QV.index); QV = QV.reindex(idx)[coins].to_numpy()
USD = 200_000 * 2.0


def run(f, okx=False, five=False, coin_set=None):
    ev = []
    for j, c in enumerate(coins):
        if coin_set is not None and c not in coin_set:
            continue
        for t in np.flatnonzero(np.isfinite(sd[:, j])):
            if t == 0 or not np.isfinite(C[t - 1, j]):
                continue
            lim = C[t - 1, j] * (1 - 3 * sd[t, j])
            if not (np.isfinite(Lw[t, j]) and Lw[t, j] <= lim * (1 - 2e-4)):
                continue
            if okx and not (c in OKL and np.isfinite(OKL[c][t]) and OKL[c][t] <= lim * (1 - 2e-4)):
                continue
            px = lim
            if five:
                k = K5[c].loc[idx[t]:idx[t] + pd.Timedelta(minutes=55)]; below = k[k <= lim]
                if below.empty:
                    continue
                px = float(below.iloc[0])
            size = min(0.1, f * np.nan_to_num(QV[t, j]) / USD)
            if size > 0:
                ev.append((t, j, px, size))
    ev.sort(); ends = []; p = np.zeros(n); sizes = []
    for t, j, px, s in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5 or t + 4 >= n:
            continue
        ends.append(t + 4); sizes.append(s); p[t] += s * (C[t, j] / px - 1) - s * 2e-4
        for k in range(t + 1, t + 5):
            p[k] += s * (C[k, j] / C[k - 1, j] - 1) - s * fh[k, j]
        p[t + 4] -= s * 5e-4
    return pd.Series(p, index=idx), float(np.mean(sizes)) if sizes else 0.0


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
out = {}; keep = {}
for f in (0.01, 0.005):
    for nm, kw in (("a Binance fill", {}), ("b OKX-confirmed", dict(okx=True)), ("c pack, 5-minute close", dict(five=True, coin_set=set(pk)))):
        h, ms = run(f, **kw); k = f"{nm}, f = {f:.1%}"; out[k] = {"D/T/H": per(h), "mean size (unit 0.1 = full)": round(ms, 4)}; keep[k] = h
        print(k, out[k], flush=True)
h = keep["a Binance fill, f = 1.0%"]; vd = L.V7.groupby(L.V7.index.floor("D")).sum(); d = h.groupby(h.index.floor("D")).sum()
out["corr v8.6 (a, 1%)"] = round(float(pd.concat([d, vd], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
b = L.book([h.reindex(L.H6.index).fillna(0.0).rename("crash limit buys")]); k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
Rf = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
out["v8.6 + capped sleeve (a, 1%)"] = {"D/T/H": k, "strict pass": bool(all(a >= q for a, q in zip(k[1:], Rf[1:])) and k[0] >= Rf[0] + 0.05)}
out["VERDICT capacity-real"] = bool(all(x >= 1.0 for x in out["b OKX-confirmed, f = 1.0%"]["D/T/H"]) and all(x >= 0.5 for x in out["c pack, 5-minute close, f = 1.0%"]["D/T/H"]))
print(json.dumps({k: out[k] for k in ("corr v8.6 (a, 1%)", "v8.6 + capped sleeve (a, 1%)", "VERDICT capacity-real")}), flush=True)
json.dump(out, open(ROOT / "results/gen352c.json", "w"), indent=1)
for k, v in keep.items():
    v.to_frame("p").to_parquet(ROOT / f"results/gen352c_{k[0]}_{k.split('= ')[1].replace('%', 'pct')}.parquet")
