"""Gen354 (config/gen354_protocol.json): fast premium rank, daily / 3 tranches / banded. Writes results/gen354.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, CS, coins, Hc, idx, n, zz, pk, END, ROOT = (g[k] for k in ("L", "B", "X", "CS", "coins", "Hc", "idx", "n", "zz", "pk", "END", "ROOT"))
Zp = {}
for c in coins:
    p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); Zp[c] = zz(p.reindex(idx))
Zp = pd.DataFrame(Zp, index=idx)
z23 = Zp[Zp.index.hour == 23]; z23.index = z23.index.floor("D")
P = Hc.resample("1D").last(); listed = P.notna().cumsum() >= 60; vol = P.pct_change(fill_method=None).rolling(30).std()
z23 = z23.reindex(P.index)
rk = z23.where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed & z23.notna())
wl, ws = iv.where(rk <= 1 / 3, 0.0), iv.where(rk > 2 / 3, 0.0)
w = ((wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)) * 0.5).fillna(0.0)


def band(w, b=0.02):
    A = w.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1])
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) > b; ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    return pd.DataFrame(E, index=w.index, columns=w.columns)


S = {"A daily": w, "B 3 tranches": CS._hold(w, 3, True), "C daily with a no-trade band": band(w)}
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum()
cr = {k: v.groupby(v.index.floor("D")).sum() for k, v in (("premium carry", L.H6["premium carry"]), ("premium carry 60", L.ALTK[-1]))}
out = {}
for nm, ww in S.items():
    h = CS.premium_carry_breadth(coins=coins, w=ww).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "corr carry 20 / carry 60": [round(float(pd.concat([d, x], axis=1).loc["2020":END].corr().iloc[0, 1]), 3) for x in cr.values()],
               "daily turnover": round(float(ww.diff().abs().sum(axis=1).mean()), 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen354_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen354.json", "w"), indent=1)
