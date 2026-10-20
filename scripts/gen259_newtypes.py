"""Gen259 (config/gen259_protocol.json): PCA stat-arb, funding TS carry, NR7 breakout, Asian-range breakout. Writes results/gen259.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
B, END = L.B, L.END
out = {}; save = lambda: json.dump(out, open(L.ROOT / "results/gen259.json", "w"), indent=1)
C = B.coins(); P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
H6IDX = L.H6.index

# ---- A PCA stat-arb
W = pd.DataFrame(0.0, index=R.index, columns=C); state = pd.Series(0.0, index=C)
Rv = R.to_numpy(); idx = R.index
for t in range(150, len(idx)):
    win = R.iloc[t - 89:t + 1]; ok = win.notna().all().to_numpy()
    if ok.sum() < 10:
        W.iloc[t] = 0.0; continue
    X = win.loc[:, ok]; Z = (X - X.mean()) / X.std()
    u, s_, vt = np.linalg.svd(Z.to_numpy(), full_matrices=False); Fct = Z.to_numpy() @ vt[:3].T
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(len(Fct)), Fct], X.to_numpy(), rcond=None)
    res = X.to_numpy() - np.c_[np.ones(len(Fct)), Fct] @ beta
    cum = np.cumsum(res[-60:], axis=0); sc = (cum[-1] - cum.mean(axis=0)) / cum.std(axis=0)
    cols = X.columns; st = state.copy(); st[~st.index.isin(cols)] = 0.0
    for j, c in enumerate(cols):
        if st[c] == 0 and sc[j] < -1.25: st[c] = 0.1
        elif st[c] == 0 and sc[j] > 1.25: st[c] = -0.1
        elif st[c] != 0 and abs(sc[j]) < 0.5: st[c] = 0.0
    state = st
    rb = R["BTC"].iloc[t - 89:t + 1]; bet = X.apply(lambda y: y.cov(rb) / rb.var())
    w = st.copy(); w["BTC"] = w.get("BTC", 0.0) - float((st[cols] * bet).sum()) + (st.get("BTC", 0.0) * float(bet.get("BTC", 1.0)))
    W.iloc[t] = w.reindex(C).fillna(0.0).to_numpy()
L.judge("A PCA stat-arb", L.perp(W), out); save()

# ---- B funding time-series carry
fu = B.funding_panel(["BTC", "ETH"]); fu.index = (fu.index - pd.Timedelta(seconds=1)).floor("D"); fd = fu.groupby(level=0).sum().reindex(R.index)
f7 = fd.rolling(7).mean(); z = (f7 - f7.rolling(365, min_periods=180).mean()) / f7.rolling(365, min_periods=180).std()
wB = pd.DataFrame(np.where(z > 1, -0.25, np.where(z < -1, 0.25, 0.0)), index=R.index, columns=["BTC", "ETH"])
L.judge("B funding TS carry", L.perp(wB), out); F.judge("B funding TS carry", F.cfd(wB), out); save()


# ---- C / D intraday breakouts on 5-minute bars
def breakout(coin, kind):
    k = B.k5(coin).loc[:END + " 23:55"]; day = k.index.floor("D")
    o, h, l, c = k.open.to_numpy(), k.high.to_numpy(), k.low.to_numpy(), k.close.to_numpy()
    dh, dl = k.high.groupby(day).max(), k.low.groupby(day).min(); rng = dh - dl
    trades = {}
    groups = pd.Series(np.arange(len(k)), index=k.index).groupby(day)
    for d, ix in groups:
        ix = ix.to_numpy()
        if kind == "nr7":
            prev = d - pd.Timedelta(days=1)
            if prev not in rng.index or rng.loc[:prev].tail(7).shape[0] < 7 or rng[prev] > rng.loc[:prev].tail(7).min():
                continue
            hi, lo, scan = dh[prev], dl[prev], ix
        else:
            hrs = k.index[ix].hour; asia = ix[hrs < 7]; scan = ix[(hrs >= 7) & (hrs < 21)]
            if len(asia) < 60 or len(scan) == 0:
                continue
            hi, lo = h[asia].max(), l[asia].min()
        for i in scan:
            if h[i] > hi:
                trades[d] = (1, max(o[i], hi), c[ix[-1]]); break
            if l[i] < lo:
                trades[d] = (-1, min(o[i], lo), c[ix[-1]]); break
    return trades


def to_hourly(trades_by_coin, cost_of):
    pnl = pd.Series(0.0, index=H6IDX)
    for coin, tr in trades_by_coin.items():
        for d, (side, ent, ex) in tr.items():
            t = d + pd.Timedelta(hours=23)
            if t in pnl.index:
                pnl[t] += 0.5 * (side * (ex / ent - 1) - 2 * cost_of(coin))
    return pnl


for name, kind in (("C NR7 breakout", "nr7"), ("D Asian-range breakout", "asia")):
    T = {c: breakout(c, kind) for c in ("BTC", "ETH")}
    out[name + " trades"] = int(sum(len(v) for v in T.values()))
    L.judge(name, to_hourly(T, lambda c: 5e-4), out)
    hb = to_hourly(T, lambda c: (F.CB.SPREAD[c] + F.CB.COMM) / 1e4).reindex(F.IDXbf).fillna(0.0)
    F.judge(name, hb, out); save()
