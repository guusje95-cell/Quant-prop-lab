"""Gen426 (config/gen426_protocol.json, FLAGGED): Gen425 listing short with a per-event stop. Writes results/gen426.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else float("nan")
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95))
TF = set(json.load(open(ROOT / "config/tradfi_perps.json"))["symbols"])
P = ROOT / "research_data/binance_pit"; EV = []
for f in sorted(glob.glob(str(P / "*_1h.parquet"))):
    if f.endswith("premium_1h.parquet"):
        continue
    s = Path(f).name.replace("_1h.parquet", "")
    if s in TF:
        continue
    k = pd.read_parquet(f); k.index = pd.DatetimeIndex(k.index)
    t0 = k.index.min()
    if t0 < pd.Timestamp("2021-06-01") or k.loc[:t0 + pd.Timedelta(hours=23), "quote_volume"].sum() < 1e7:
        continue
    fu = pd.read_parquet(P / f"{s}_funding.parquet"); fu.index = pd.to_datetime(fu["time"]).dt.floor("h")
    EV.append((s, t0, k["close"], fu["last_funding_rate"].groupby(level=0).sum(), k.loc[:t0 + pd.Timedelta(hours=23), "quote_volume"].sum()))
print("events", len(EV), flush=True)
def sleeve(H, stop=0.30, cm=1.0, minvol=1e7):
    pos = pd.DataFrame(0.0, index=idx, columns=[e[0] for e in EV]); R = pos.copy(); F = pos.copy(); n = 0
    for s, t0, c, fr, v0 in EV:
        start = (t0 + pd.Timedelta(hours=24)).ceil("D"); end = min(start + pd.Timedelta(days=H), c.index.max())
        if start >= end or start > idx[-1] or v0 < minvol:
            continue
        cc = c.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * (1 + stop)].index
        if len(hit):
            end = min(end, hit[0] + pd.Timedelta(hours=1))           # covered at that close: flat from the next hour
        m = (idx >= start) & (idx < end); pos.loc[m, s] = -0.05; n += 1
        R[s] = c.pct_change().shift(-1).reindex(idx).fillna(0.0); f = fr.copy(); f.index = f.index - pd.Timedelta(hours=1); F[s] = f.reindex(idx).fillna(0.0)
    g = pos.abs().sum(axis=1); pos = pos.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    pnl = (pos * R).sum(axis=1) - (pos * F).sum(axis=1) - pos.diff().abs().sum(axis=1).fillna(0.0) * 10 * cm / 1e4
    return pnl, g, n
s, g, n = sleeve(30); b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.5": [REF[0], REF[1]], "events used": n, "sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)},
       "corr book": round(float(dd(s).corr(dd(v95))), 2), "mean gross": round(float(g.loc["2022":].mean()), 3), "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3))), "robustness": {}}
for k, kw in (("stop 20%", dict(stop=0.20)), ("stop 50%", dict(stop=0.50)), ("costs x2", dict(cm=2.0)), ("first-day volume >= $50M", dict(minvol=5e7))):
    out["robustness"][k] = per(sleeve(30, **kw)[0])
for H in (14, 60):
    out["robustness"][f"hold {H}"] = per(sleeve(H)[0])
print(json.dumps(out))
(ROOT / "results/gen426.json").write_text(json.dumps(out, indent=1))
