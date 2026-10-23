"""Gen352 (config/gen352_protocol.json): crash limit buys and USDT premium spikes. Writes results/gen352.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, coins, Hc, idx, n, pnl, zz, pk, END, ROOT, R, fund = (g[k] for k in ("L", "B", "X", "coins", "Hc", "idx", "n", "pnl", "zz", "pk", "END", "ROOT", "R", "fund"))
LO = pd.concat([B.panel("low", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in coins if c not in pk], axis=1)
LO = LO[~LO.index.duplicated()]; LO.index = pd.DatetimeIndex(LO.index); LO = LO.reindex(idx)[coins]
C = Hc.to_numpy(); Lw = LO.to_numpy(); sd = R.where(Hc.notna()).rolling(720, min_periods=500).std().shift(1).to_numpy()
pnl_h = np.zeros(n); ev = []
for j in range(len(coins)):
    for t in range(1, n):
        lim = C[t - 1, j] * (1 - 3 * sd[t, j]) if np.isfinite(sd[t, j]) and np.isfinite(C[t - 1, j]) else np.nan
        if np.isfinite(lim) and np.isfinite(Lw[t, j]) and Lw[t, j] <= lim * (1 - 2e-4):
            ev.append((t, j, lim))
ev.sort(); ends = []; fh = fund.to_numpy()
for t, j, lim in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5 or t + 4 >= n:
        continue
    ends.append(t + 4)
    pnl_h[t] += 0.1 * (C[t, j] / lim - 1) - 0.1 * 2e-4                     # fill hour: from the limit price to the close
    for k in range(t + 1, t + 5):
        pnl_h[k] += 0.1 * (C[k, j] / C[k - 1, j] - 1) - 0.1 * fh[k, j]
    pnl_h[t + 4] -= 0.1 * 5e-4
S = {"A crash limit buys": pd.Series(pnl_h, index=idx)}
ut = pd.read_parquet(ROOT / "research_data/coinbase/USDT-USD_1h.parquet")["close"]; ut.index = pd.DatetimeIndex(ut.index); ut = ut[~ut.index.duplicated()].reindex(idx)
z = np.nan_to_num(zz(ut - 1)); P = np.zeros((n, len(coins)))
for t in np.flatnonzero(np.abs(z) > 3):
    for c in ("BTC", "ETH"):
        P[t + 1:min(t + 5, n), coins.index(c)] = 0.25 * np.sign(z[t])
S["B USDT premium hourly spike"] = pnl(pd.DataFrame(P, index=idx, columns=coins))
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {"A fills": len(ev)}
for nm, h in S.items():
    h = h.reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen352_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen352.json", "w"), indent=1)
