"""Gen411 (config/gen411_protocol.json). Writes results/gen411.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
dd, shp, per, unit, END, CS, V, B, pnl, days, C6, rc6, a, bsm, R, FU, prep, idx = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "B", "pnl", "days", "C6", "rc6", "a", "bsm", "R", "FU", "prep", "idx"))
rc95 = (rc6 + a + bsm) / 3; V5 = V.assign(**{"relative crowding 6": rc95}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
def weighted(Hk, col, m):
    ph0, W, mult = CS.portfolio_v5(Hk); W2 = W.copy(); W2[col] *= m
    Wh = W2.reindex(Hk.index.floor("D")).set_axis(Hk.index); raw = (Hk * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    tgt = (0.15 / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    return unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
# B: 4-hourly component
def rel4(col):
    Z = {}
    for c in C6:
        m = B.metrics(c)[col]; m.index = pd.DatetimeIndex(m.index); x = m.resample("4h").mean()
        Z[c] = (x - x.rolling(540, min_periods=380).mean()) / x.rolling(540, min_periods=380).std()
    Z = pd.DataFrame(Z); Zd = Z.sub(Z.mean(axis=1), axis=0); return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
def pnl4(W):
    out = 0.0
    for c in W:
        prep(c); p = W[c].copy(); p.index = p.index + pd.Timedelta(hours=4)
        p = p.reindex(idx, method="ffill").fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
    return out
h4 = ((pnl4(rel4("count_toptrader_long_short_ratio")) + pnl4(rel4("count_long_short_ratio"))) / 2).reindex(V.index).fillna(0.0)
# C: crowding x momentum
z_ = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def dly(s, how="mean"):
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = getattr(s.groupby(level=0), how)(); return s.reindex(days).ffill().shift(1)
P = pd.DataFrame({c: B.k5(c).close.resample("1D").last() for c in C6}).reindex(days).shift(1)
cm = {}
for col in ("count_toptrader_long_short_ratio", "count_long_short_ratio"):
    raw = pd.DataFrame({c: dly(B.metrics(c)[col]) for c in C6}); Zc = raw.apply(lambda s: z_(s, 90)); dch = raw.diff(7); r7 = P / P.shift(7) - 1
    keep = (np.sign(r7) == np.sign(dch)); Zk = Zc.where(keep); Zd = Zk.sub(Zk.mean(axis=1), axis=0)
    cm[col] = (-0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)
cxm = ((pnl(cm["count_toptrader_long_short_ratio"]) + pnl(cm["count_long_short_ratio"])) / 2).reindex(V.index).fillna(0.0)
T = {"A relative crowding weight x1.5": weighted(V5, "relative crowding 6", 1.5),
     "B + 4-hourly component": unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": (rc6 + a + bsm + h4) / 4}))[0]),
     "C crowding x momentum": unit(CS.portfolio_v5(V5.assign(**{"crowding x momentum": cxm}))[0])}
out = {"reference v9.5": [REF[0], REF[1]], "4-hourly sleeve": per(h4), "crowding x momentum sleeve": per(cxm), "trials": {}}
for k, b in T.items():
    r = [shp(b), per(b)]; out["trials"][k] = {"book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen411.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
