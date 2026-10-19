"""Gen106 (config/gen106_protocol.json): hourly opening imbalance and 16:00 London fixing reversal at BrightFunded costs.
Writes results/gen106.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen105_demand.py")}
src = open(ROOT / "scripts/gen105_demand.py").read()
exec(src.split("fx = pd.read_parquet")[0] + src[src.index("def book(p):"):src.index("b0, H0 = book(pos)")], g)
CB, B, R, pos, IDX, book, per, sh = (g[k] for k in ("CB", "B", "R", "pos", "IDX", "book", "per", "sh"))
END = "2026-09-30 23:00"
COST = pd.Series({c: (CB.SPREAD[c] + CB.COMM) for c in CB.CFD})


def sleeve(posf):
    p = posf.reindex(index=IDX, columns=CB.CFD).fillna(0.0)
    turn = p.diff().abs().fillna(p.abs()).mul(COST / 1e4, axis=1).sum(axis=1)
    return (p * R).sum(axis=1) - turn


def imbalance_pos(filtered=False):
    out = pd.DataFrame(0.0, index=IDX, columns=CB.CFD)
    for c in ("BTC", "ETH"):
        k = B.k5(c).loc[:END]; first = k[k.index.minute == 0]
        imb = ((2 * first["taker_buy_volume"] - first["volume"]) / first["volume"]).replace([np.inf, -np.inf], np.nan)
        imb.index = imb.index.floor("h")                            # signal of hour h, known at h:05
        sgn = np.sign(imb)
        if filtered:
            thr = imb.abs().rolling(24 * 30, min_periods=24 * 10).quantile(0.8).shift(1)
            sgn = sgn.where(imb.abs() > thr, 0.0)
        sgn = sgn.reindex(IDX).fillna(0.0)
        out[c] = 0.5 * sgn.shift(1).rolling(4, min_periods=1).mean()   # hours h+1 .. h+4
    return out


def fixing_pos():
    out = pd.DataFrame(0.0, index=IDX, columns=CB.CFD)
    days = pd.date_range("2020-01-01", "2026-09-30")
    for c in ("BTC", "ETH"):
        o = B.k5(c).open.resample("1h").first()
        for d in days:
            lon = lambda h: (pd.Timestamp(d).tz_localize("Europe/London") + pd.Timedelta(hours=h)).tz_convert("UTC").tz_localize(None)
            t15, t16, t18 = lon(15), lon(16), lon(18)
            if t15 in o.index and t16 in o.index and o[t15] > 0:
                s = -np.sign(o[t16] / o[t15] - 1)
                out.loc[t16:t18 - pd.Timedelta(hours=1), c] = 0.5 * s
    return out


b0, H0 = book(pos); k0 = per(b0, "2022-01-01"); B0 = sh(b0, "2022-01-01", "2026-09-30")
print("BrightFunded book", round(B0, 3), "TEST/HOLD", np.round(k0[1:], 3), flush=True)
rows = []
for name, pf, prim in (("I1 hourly opening imbalance (PRIMARY)", imbalance_pos(), True), ("I1b imbalance, top-20% signals only", imbalance_pos(True), False),
                       ("F1 16:00 London fixing reversal (PRIMARY)", fixing_pos(), True)):
    h = sleeve(pf); p = per(h)
    H = pd.concat([H0, h.rename(name)], axis=1)
    import crypto_sleeves as CS
    ph, W, m = CS.portfolio_v5(H)
    k1 = per(ph, "2022-01-01"); bA = sh(ph, "2022-01-01", "2026-09-30")
    r = {"test": name, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "turnover/day": float(pf.diff().abs().sum(axis=1).loc["2022":].mean() * 24),
         "book before": B0, "book after": bA, "book TEST/HOLD after": np.round(k1[1:], 3).tolist()}
    r["pass"] = bool(prim and p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and bA > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen106.csv", index=False)
print("done", flush=True)
