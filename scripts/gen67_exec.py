"""Gen67 execution tests (config/gen67_protocol.json): cascade limit entries, C* weekly rebalance and no-trade band.
Writes results/gen67_exec.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_cascade_hourly as CH
import gen52_optimize as G
from qpl.lab import binance_pack as B, strategies as S

sh = lambda x, a, b: x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(365)
rows = []


def cascade(limit=0.0, K=3, H=12, k=3.0, size=0.2):
    ev = []
    for coin in B.coins():
        d = CH.hourly(coin).loc[:"2026-09-30 23:00"]; c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
        r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
        atr = (hi - lo).rolling(14).mean(); e = (r < -k * sd) & (doi < -0.05) & (v > vq)
        cv, lov, atv = c.to_numpy(), lo.to_numpy(), atr.to_numpy(); n = len(cv)
        for t in np.flatnonzero(e.to_numpy()):
            if t + 1 >= n:
                continue
            stop = lov[t] - atv[t]
            if limit > 0:
                px = cv[t] * (1 - limit)
                if lov[t + 1] > px:
                    continue                                          # not filled
                entry, cin, first = px, 2 / 1e4, t + 1                # stop can trigger in the fill hour
            else:
                entry, cin, first = cv[t], 5 / 1e4, t + 1
            ex = None
            for j in range(first, min(t + 1 + H, n)):
                if lov[j] <= stop:
                    ex = (j, min(stop, entry)); break
            if ex is None:
                ex = (min(t + H, n - 1), cv[min(t + H, n - 1)])
            ev.append((c.index[t], coin, c.index[ex[0]], ex[1] / entry - 1 - cin - 5 / 1e4))
    ev.sort(key=lambda x: (x[0], x[1])); open_ex, pnl = [], {}
    for t0, coin, t1, ret in ev:
        open_ex = [x for x in open_ex if x > t0]
        if len(open_ex) >= K:
            continue
        open_ex.append(t1); dd = t1.floor("D"); pnl[dd] = pnl.get(dd, 0.0) + size * ret
    return pd.Series(pnl).sort_index().reindex(pd.date_range("2021-12-01", "2026-09-30")).fillna(0.0), len(ev)


for nm, lim in (("E1 base: cascade market entry", 0.0), ("E1 cascade limit entry -0.25%", 0.0025), ("E1 cascade limit entry -0.5%", 0.005)):
    x, n = cascade(lim)
    rows.append({"test": nm, "events": n, "DEV(2022)": sh(x, "2022", "2022"), "TEST": sh(x, "2023", "2024"), "HOLD": sh(x, "2025", "2026"), "2023+": sh(x, "2023", "2026")})
    print(rows[-1], flush=True)

# C* execution on perps with funding
C10 = B.MAJ10
cs = S.CStarTrend(); W, _ = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0); W = W[C10]
P = B.panel("close", "1D", C10).loc[:"2026-09-30"]; R = P.pct_change(fill_method=None)
F = B.funding_panel(C10); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
idx = P.index[P.index >= "2020-01-02"]


def run(w):
    held = w.reindex(idx).fillna(0.0).shift(1).fillna(0.0)
    return (held * R.reindex(idx).fillna(0) - held * FD.reindex(idx).fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * 7.5 / 1e4


w0 = W.reindex(idx).fillna(0.0)
ww = w0.copy(); prev = w0.iloc[0] * 0
for d in idx:
    cur = w0.loc[d]
    new = prev.copy() if d.dayofweek != 0 else cur.copy()
    new[cur == 0] = 0.0                                                 # exits always executed
    ww.loc[d] = new; prev = new
wb = w0.copy(); prev = w0.iloc[0] * 0
for d in idx:
    cur = w0.loc[d].copy()
    keep = (prev != 0) & (cur != 0) & ((cur - prev).abs() < 0.25 * prev.abs())
    cur[keep] = prev[keep]; wb.loc[d] = cur; prev = cur
for nm, w in (("E2/E3 base: C* daily rebalance", w0), ("E2 C* weekly rebalance (exits daily)", ww), ("E3 C* 25% no-trade band", wb)):
    x = run(w); turn = w.diff().abs().sum(axis=1).mean() * 365
    rows.append({"test": nm, "annual_turnover": turn, "DEV": sh(x, "2020", "2022"), "TEST": sh(x, "2023", "2024"), "HOLD": sh(x, "2025", "2026"), "2023+": sh(x, "2023", "2026")})
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen67_exec.csv", index=False)
