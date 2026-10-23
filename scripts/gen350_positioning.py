"""Gen350 (config/gen350_protocol.json): OI spike fade, top-trader crowding, taker ratio spikes. Writes results/gen350.json."""
import json
import numpy as np
import pandas as pd
_src = open(__import__("pathlib").Path(__file__).resolve().parent / "gen349_dislocations.py").read()
g = {"__file__": __file__}; exec(compile(_src.split("\nS = {}")[0], "gen349", "exec"), g)
L, B, X, coins, Hc, idx, n, pnl, zz, pk, END, ROOT = (g[k] for k in ("L", "B", "X", "coins", "Hc", "idx", "n", "pnl", "zz", "pk", "END", "ROOT"))
ret1 = Hc.pct_change(fill_method=None)


def ev_pos(Z, direction):
    P = np.zeros((n, len(coins)))
    for c, z in Z.items():
        z = np.nan_to_num(z); j = coins.index(c); d = direction(c)
        for t in np.flatnonzero(np.abs(z) > 3):
            s = d[t] if d is not None else -np.sign(z[t])
            if s:
                P[t + 1:min(t + 5, n), j] = 0.1 * s
    return pd.DataFrame(P, index=idx, columns=coins)


OI = {}
for c in coins:
    if c in pk:
        o = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last()
    else:
        o = pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_oi_1h.parquet")["oi_value"]; o.index = pd.DatetimeIndex(o.index); o = o[~o.index.duplicated()]
    OI[c] = zz(np.log(o.where(o > 0)).diff().reindex(idx))
S = {"A open-interest spike fade": ev_pos(OI, lambda c: -np.sign(np.nan_to_num(ret1[c].to_numpy())))}
TT, TK = {}, {}
for c in pk:
    m = B.metrics(c)
    TT[c] = zz(m["sum_toptrader_long_short_ratio"].resample("1h").last().diff().reindex(idx))
    TK[c] = zz(m["sum_taker_long_short_vol_ratio"].resample("1h").mean().reindex(idx))
S["B top-trader crowding"] = ev_pos(TT, lambda c: None); S["C taker volume ratio spike"] = ev_pos(TK, lambda c: None)
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm, P in S.items():
    h = pnl(P).reindex(L.H6.index).fillna(0.0); first = str(P.abs().sum(axis=1).ne(0).idxmax().date())
    s = [round(x, 3) for x in L.per(h, max(first, "2020-01-01"))]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"first trade": first, "sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "gross": [round(x, 3) for x in L.per(pnl(P, 0.0).reindex(L.H6.index).fillna(0.0), max(first, "2020-01-01"))],
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen350_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen350.json", "w"), indent=1)
