"""Gen341 (config/gen341_protocol.json): funding-settlement pressure, residual reversal, pump reversal; correlation with v8.6.
Writes results/gen341.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END
vd = L.V7.groupby(L.V7.index.floor("D")).sum()
coins = CS._breadth_universe(); Hc = CS._breadth_close(coins); R1 = Hc.pct_change(fill_method=None)
pk = B.coins()
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fh = fund.copy(); fh.index = fh.index - pd.Timedelta(hours=1); fh = fh.groupby(level=0).sum().reindex(Hc.index).fillna(0.0)
out = {"reference v8.6": [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()}

# A: funding-settlement pressure (pack coins)
FP = B.funding_panel(pk); hp = Hc[pk]; rp = R1[pk].fillna(0.0)
posA = pd.DataFrame(0.0, index=hp.index, columns=pk)
for c in pk:
    f = FP[c].dropna(); prev = f.shift(1)
    sig = pd.Series(np.where(prev > 0.0003, -0.1, np.where(prev < -0.0001, 0.1, 0.0)), index=f.index)
    bar = sig.index - pd.Timedelta(hours=1)                                  # the hour bar ending at the settlement
    posA.loc[posA.index.intersection(bar), c] = sig.set_axis(bar).reindex(posA.index.intersection(bar)).to_numpy()
A = (posA * rp).sum(axis=1) - posA.diff().abs().fillna(0.0).sum(axis=1) * 5 / 1e4

# B: residual reversal
P = Hc.resample("1D").last(); dr = P.pct_change(fill_method=None); listed = P.notna().cumsum() >= 60; vol = dr.rolling(30).std()
beta = dr.rolling(60, min_periods=50).cov(dr["BTC"]).div(dr["BTC"].rolling(60, min_periods=50).var(), axis=0)
res = dr - beta.mul(dr["BTC"], axis=0)
rk = (-res).where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed)
wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
w = (wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)).fillna(0.0)
Bs = CS.premium_carry_breadth(coins=coins, w=CS._hold(w, 3, True)).loc[:END + " 23:00"]

# C: pump reversal
sd = R1.rolling(720, min_periods=500).std().shift(1); ev = (R1 > 4 * sd)
posC = pd.DataFrame(0.0, index=Hc.index, columns=coins); openq = []
evi = np.argwhere(ev.fillna(False).to_numpy())
evi = evi[np.argsort(evi[:, 0], kind="stable")]
PC = posC.to_numpy().copy(); n = len(Hc)
for t, j in evi:
    openq = [e for e in openq if e > t]
    if len(openq) >= 3 or t + 1 >= n:
        continue
    PC[t + 1:min(t + 13, n), j] -= 0.2; openq.append(min(t + 12, n - 1))
posC = pd.DataFrame(PC, index=Hc.index, columns=coins)
C = (posC * R1.fillna(0.0)).sum(axis=1) - (posC * fh).sum(axis=1) - posC.diff().abs().fillna(0.0).sum(axis=1) * 5 / 1e4

for nm, h in (("A funding-settlement pressure", A), ("B residual reversal", Bs), ("C pump reversal", C)):
    h = h.loc[:END + " 23:00"]
    d = h.groupby(h.index.floor("D")).sum(); c = float(pd.concat([d, vd], axis=1, sort=True).loc["2020-01-01":END].dropna().corr().iloc[0, 1])
    s = [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
    b = L.book([h.reindex(L.H6.index).fillna(0.0).rename(nm)]); k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
    R = out["reference v8.6"]
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr with v8.6 (daily 2020-26)": round(c, 3),
               "orthogonal candidate": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2),
               "v8.6 with it D/T/H": k, "strict pass": bool(all(a >= q for a, q in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05)}
    print(nm, out[nm], flush=True)
json.dump(out, open(L.ROOT / "results/gen341.json", "w"), indent=1)
