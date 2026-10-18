"""Gen94 (config/gen94_protocol.json): bounce-family ensemble and 4-hourly deleveraging bounce. Writes results/gen94.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
inner = g["g"]
B, CFD, fhp, d2h, IDX, dsh, hold_w, P, R, QV, bk = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "dsh", "hold_w", "P", "R", "QV", "bk"))
BASE = dict(g["BASE"]); B0 = g["B0"]; oi_weights = inner["oi_weights"]
idx = P.index; Z = lambda: pd.DataFrame(0.0, index=idx, columns=["BTC", "ETH"])
legs = {}
legs["H4"] = oi_weights(["BTC", "ETH"]).reindex(idx).fillna(0.0)
sd30 = R.rolling(30).std().shift(1); ma = P.rolling(100).mean(); w = Z(); active = {}
for d in idx:                                                                   # R4 dip-buy (Gen63 I5 rule)
    active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
    for c in ("BTC", "ETH"):
        if R.at[d, c] < -2.5 * sd30.at[d, c] and P.at[d, c] > ma.at[d, c] and c not in active and len(active) < 3:
            active[c] = 3
    for c in active:
        w.at[d, c] = 0.2
legs["R4 dip"] = w
w = Z()
for c in ("BTC", "ETH"):
    dv = pd.read_parquet(ROOT / f"data/raw/deribit/{c}_DVOL.parquet")["close"]; dv.index = pd.DatetimeIndex(dv.index).tz_localize(None).normalize(); dv = dv.reindex(idx)
    w[c] = hold_w((dv / dv.shift(1) - 1 > 0.10) & (R[c] < 0)).to_numpy()
legs["L1 DVOL"] = w
w = Z()
for c in ("BTC", "ETH"):
    w[c] = hold_w((QV[c] > 3 * QV[c].shift(1).rolling(30).mean()) & (R[c] < 0)).to_numpy()
legs["L2 volume"] = w
w = Z()
for c in ("BTC", "ETH"):
    pm = B.premium(c)["close"]; pdd = pm.groupby(pm.index.floor("D")).mean().reindex(idx)
    w[c] = hold_w(pdd < pdd.shift(1).rolling(365, min_periods=180).quantile(0.05)).to_numpy()
legs["M2 discount"] = w
w = Z()
for c in ("BTC", "ETH"):
    f = B.funding(c); f = f[(f.index.hour.isin([0, 8, 16])) & (f.index.minute == 0)]
    an = (f < 0).groupby(f.index.floor("D")).agg(lambda x: bool(len(x) == 3 and x.all())).reindex(idx).fillna(False).astype(bool)
    w[c] = hold_w(an & (P[c] / P[c].shift(3) - 1 < 0)).to_numpy()
legs["M3 funding"] = w
ens = sum(legs.values()) / len(legs)
to_h = lambda ww: fhp(d2h(ww.reindex(columns=CFD).fillna(0.0)), 3.3).reindex(IDX).fillna(0.0)
h4 = BASE["delev bounce"]
per = lambda h, d0: (dsh(h, d0, "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
ROWS = []
ref = per(h4, "2022-01-01"); print("H4 sleeve DEV/TEST/HOLD", np.round(ref, 2), "book", round(B0, 3), flush=True)
for k, ww in legs.items():
    print("   leg", k, np.round(per(to_h(ww), "2020-01-01"), 2), "active days", int((ww.sum(axis=1) > 0).sum()), flush=True)
hF = to_h(ens); pF = per(hF, "2020-01-01"); bF = dsh(bk({**BASE, "delev bounce": hF}), "2022-01-01", "2026-09-30")
ROWS.append({"test": "F1 bounce-family ensemble (replaces H4)", "DEV": pF[0], "TEST": pF[1], "HOLD": pF[2], "H4 TEST": ref[1], "H4 HOLD": ref[2],
             "book before": B0, "book after": bF, "pass": bool(pF[0] > 0 and pF[1] > ref[1] and pF[2] > ref[2] and bF > B0)}); print(ROWS[-1], flush=True)

# F2 4-hourly check
H1 = {c: B.k5(c).close.resample("1h").last() for c in ("BTC", "ETH")}
pos = pd.DataFrame(0.0, index=IDX, columns=CFD)
for c in ("BTC", "ETH"):
    m = B.metrics(c)["sum_open_interest_value"]; m = m.where(m > 0).resample("1h").last().ffill(); px = H1[c]
    checks = pd.date_range("2021-12-02", "2026-09-30 20:00", freq="4h"); t = checks - pd.Timedelta(minutes=5)
    f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
    sig = (f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -0.10) & (f(px, t) < f(px, t - pd.Timedelta(days=1)))
    until = pd.Timestamp("2000-01-01"); col = pos[c].to_numpy().copy(); ix = {ts: i for i, ts in enumerate(IDX)}
    for ts, s in zip(checks, sig):
        if s and ts >= until and ts in ix:
            i = ix[ts]; col[i:i + 48] = 0.5; until = ts + pd.Timedelta(hours=48)
    pos[c] = col
hQ = fhp(pos, 3.3).reindex(IDX).fillna(0.0); pQ = per(hQ, "2022-01-01"); bQ = dsh(bk({**BASE, "delev bounce": hQ}), "2022-01-01", "2026-09-30")
ROWS.append({"test": "F2 bounce checked every 4h (replaces H4)", "DEV": pQ[0], "TEST": pQ[1], "HOLD": pQ[2], "H4 TEST": ref[1], "H4 HOLD": ref[2],
             "book before": B0, "book after": bQ, "pass": bool(pQ[0] > 0 and pQ[1] > ref[1] and pQ[2] > ref[2] and bQ > B0)}); print(ROWS[-1], flush=True)
pd.DataFrame({"F1": hF, "F2": hQ}).to_parquet(ROOT / "results/cache_gen94_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen94.csv", index=False)
print("done", flush=True)
