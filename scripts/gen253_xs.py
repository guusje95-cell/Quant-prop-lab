"""Gen253 (config/gen253_protocol.json): six crypto XS / flow ideas in v7. Writes results/gen253.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END
out = {"reference v7": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; print(out, flush=True)
save = lambda: json.dump(out, open(L.ROOT / "results/gen253.json", "w"), indent=1)
C = B.coins(); P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
QV = B.panel("quote_volume", "1D", C).loc[:END].replace(0, np.nan)
# A volume shock
L.judge("A volume shock", L.perp(L.xs(np.log(QV.rolling(7).mean() / QV.rolling(90, min_periods=60).mean()))), out); save()
# B residual momentum
alts = [c for c in C if c != "BTC"]; rb = R["BTC"]
res = {}
for c in alts:
    y = R[c]; cov = y.rolling(90, min_periods=60).cov(rb); beta = cov / rb.rolling(90, min_periods=60).var()
    e = y - beta.shift(1) * rb                                     # residual with yesterday's beta (no look-ahead)
    res[c] = e.shift(1).rolling(30, min_periods=20).sum() / e.rolling(90, min_periods=60).std()
L.judge("B residual momentum", L.perp(L.xs(pd.DataFrame(res))), out); save()
# C near the 90-day high
L.judge("C near 90-day high", L.perp(L.xs(P / P.rolling(90, min_periods=60).max())), out); save()
# D betting against beta
beta = pd.DataFrame({c: R[c].rolling(90, min_periods=60).cov(rb) / rb.rolling(90, min_periods=60).var() for c in alts})
rk = beta.rank(axis=1); cnt = beta.notna().sum(axis=1); ok = cnt >= 10
lo = rk.le(4); hi = rk.gt(cnt - 4, axis=0)
bl = beta.where(lo).mean(axis=1); bh = beta.where(hi).mean(axis=1)
sl, shh = 1 / bl, 1 / bh; m = pd.concat([sl, shh], axis=1).max(axis=1)
wL = lo.astype(float).mul(0.5 / 4 * sl / m, axis=0); wS = hi.astype(float).mul(0.5 / 4 * shh / m, axis=0)
L.judge("D betting against beta", L.perp((wL - wS).mul(ok.astype(float), axis=0).fillna(0.0)), out); save()
# E BTC vs alts rotation
alt = R[alts].mean(axis=1); rel = (1 + rb).rolling(30).apply(np.prod, raw=True) - (1 + alt).rolling(30).apply(np.prod, raw=True)
sgn = np.sign(rel).fillna(0.0)
W = pd.DataFrame(0.0, index=R.index, columns=C); W["BTC"] = 0.5 * sgn
for c in alts:
    W[c] = -0.5 / len(alts) * sgn * R[c].notna()
L.judge("E BTC-alt rotation", L.perp(W), out); save()


# F pump fade (hourly)
def pump_fade(c, k=3.0, oi_th=0.03, hold=12, size=0.2, cost=5):
    h = B.k5(c).close.resample("1h").last().loc[:END + " 23:00"]; r = h.pct_change(fill_method=None)
    sd = r.rolling(720, min_periods=480).std().shift(1)
    oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1h").last().reindex(h.index)
    doi = oi / oi.shift(1) - 1
    sig = ((r > k * sd) & (doi > oi_th)).to_numpy()
    pos = np.zeros(len(h))
    for i in np.flatnonzero(sig):
        pos[i + 1:i + 1 + hold] = -size
    pos = pd.Series(pos, index=h.index)
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(h.index).fillna(0.0)
    return pos * r.fillna(0.0) - pos * f - pos.diff().abs().fillna(0.0) * cost / 1e4, pos


legs = []; held = []
for c in C:
    p_, q_ = pump_fade(c); legs.append(p_); held.append(q_.rename(c))
H = pd.concat(held, axis=1).fillna(0.0)
scale = (H.ne(0).sum(axis=1).clip(lower=3) / 3)                    # max 3 open: scale down when more are open
pnl = (pd.concat(legs, axis=1).fillna(0.0).sum(axis=1) / scale)
out["F events"] = int(sum((q.diff() < 0).sum() for q in held)); L.judge("F pump fade", pnl, out, dev_start="2022-01-01"); save()
