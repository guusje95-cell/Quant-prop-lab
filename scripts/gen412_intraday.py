"""Gen412 (config/gen412_protocol.json): intraday timing sleeves. Writes results/gen412.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, V, B, C6, rc6, a, bsm, R, FU, prep, idx = (g[k] for k in ("shp", "per", "unit", "CS", "V", "B", "C6", "rc6", "a", "bsm", "R", "FU", "prep", "idx"))
V5 = V.assign(**{"relative crowding 6": (rc6 + a + bsm) / 3}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
def run(P):
    out = 0.0
    for c, p in P.items():
        prep(c); p = p.reindex(idx).fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
    return out.reindex(V.index).fillna(0.0)
for c in C6:
    prep(c)
H = pd.date_range(R["BTC"].index.min(), idx.max(), freq="1h")
# A intraday momentum
PA = {}
for c in ("BTC", "ETH"):
    r = R[c].reindex(H).fillna(0.0); lr = np.log1p(r)
    m = lr[lr.index.hour < 22].groupby(lr[lr.index.hour < 22].index.floor("D")).sum()
    s = pd.Series(0.0, index=H); hh = H[H.hour >= 22]
    s.loc[hh] = 0.5 * np.sign(m.reindex(hh.floor("D")).values); PA[c] = s.fillna(0.0)
# B hour-of-week seasonality
PB = {}
for c in ("BTC", "ETH"):
    r = R[c].reindex(H); how = H.dayofweek * 24 + H.hour; gr = r.groupby(how)
    mu = gr.transform(lambda s: s.shift(1).rolling(104, min_periods=52).mean()); sd = gr.transform(lambda s: s.shift(1).rolling(104, min_periods=52).std())
    n = gr.transform(lambda s: s.shift(1).rolling(104, min_periods=52).count()); t = mu / (sd / np.sqrt(n))
    PB[c] = pd.Series(np.where(t.abs() > 2, 0.5 * np.sign(mu), 0.0), index=H)
# C / D funding stamps
PC, PD = {}, {}
for c in C6:
    f = B.funding(c).copy(); f = f[~f.index.duplicated()].sort_index()
    st = f[f.index.hour.isin([0, 8, 16]) & (f.index.minute == 0)]
    prev = st.shift(1)                                                    # rate known before the coming stamp
    lab = st.index - pd.Timedelta(hours=1)
    sc = pd.Series(np.where(prev > 0.0002, -0.5, np.where(prev < 0, 0.5, 0.0)), index=lab)
    sd_ = pd.Series(np.where(st > 0.0002, 0.5, np.where(st < 0, -0.5, 0.0)), index=st.index)
    PC[c] = sc.reindex(H).fillna(0.0); PD[c] = sd_.reindex(H).fillna(0.0)
S = {"A intraday momentum BTC/ETH": run(PA), "B hour-of-week seasonality BTC/ETH": run(PB), "C pre-funding fade, 6 majors": run(PC), "D post-funding rebound, 6 majors": run(PD)}
out = {"reference v9.5": [REF[0], REF[1]], "sleeves": {}, "trials": {}}
for k, s in S.items():
    gross = None
    out["sleeves"][k] = per(s)
    b = unit(CS.portfolio_v5(V5.assign(**{k: s}))[0]); rr = [shp(b), per(b)]
    out["trials"][k] = {"book": rr, "pass": bool(rr[0] >= REF[0] + 0.05 and all(rr[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen412.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
