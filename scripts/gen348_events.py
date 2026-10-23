"""Gen348 (config/gen348_protocol.json): premium-spike reversion and short-squeeze fade. Writes results/gen348.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import gen57_cascade_hourly as CH
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); Hc = CS._breadth_close(coins).loc[:END + " 23:00"]; R = Hc.pct_change(fill_method=None).fillna(0.0); idx = Hc.index; n = len(idx)
pk = B.coins()
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(idx).fillna(0.0)
pnl = lambda pos, cost=5.0: (pos * R).sum(axis=1) - (pos * fund).sum(axis=1) - pos.diff().abs().fillna(0.0).sum(axis=1) * cost / 1e4


def posA(lag=0):
    P = np.zeros((n, len(coins)))
    for j, c in enumerate(coins):
        p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); p = p.reindex(idx)
        z = ((p - p.rolling(720, min_periods=500).mean().shift(1)) / p.rolling(720, min_periods=500).std().shift(1)).to_numpy()
        for t in np.flatnonzero(np.abs(np.nan_to_num(z)) > 3):
            P[t + 1 + lag:min(t + 5 + lag, n), j] = -0.1 * np.sign(z[t])
    return pd.DataFrame(P, index=idx, columns=coins)


def posB(lag=0):
    ev = []
    for c in pk:
        d = CH.hourly(c).reindex(idx); r = d.c.pct_change(); sd = r.rolling(720).std().shift(1); vq = d.v.rolling(720).quantile(0.95).shift(1)
        doi = d.oi.pct_change(); e = (r > 3 * sd) & (doi < -0.05) & (d.v > vq)
        ev += [(t, coins.index(c)) for t in np.flatnonzero(e.fillna(False).to_numpy())]
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 3 or t + 1 + lag >= n:
            continue
        P[t + 1 + lag:min(t + 13 + lag, n), j] -= 0.2; ends.append(t + 12)
    return pd.DataFrame(P, index=idx, columns=coins), len(ev)


vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {}
pB, nB = posB(); out["B events"] = nB
for nm, pos, pos1 in (("A premium-spike reversion", posA(), posA(1)), ("B short-squeeze fade", pB, posB(1)[0])):
    h = pnl(pos).reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6 2022-26": round(c, 3), "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2),
               "stress costs x2": [round(x, 3) for x in L.per(pnl(pos, 10.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")],
               "stress one hour later": [round(x, 3) for x in L.per(pnl(pos1).reindex(L.H6.index).fillna(0.0), "2020-01-01")],
               "gross (no costs)": [round(x, 3) for x in L.per(pnl(pos, 0.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")]}
    print(nm, out[nm], flush=True)
json.dump(out, open(ROOT / "results/gen348.json", "w"), indent=1)
