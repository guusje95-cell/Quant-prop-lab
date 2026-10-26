"""Gen425 (config/gen425_protocol.json): short newly listed Binance perps. Writes results/gen425.json."""
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
    EV.append((s, t0, k["close"], fu["last_funding_rate"].groupby(level=0).sum()))
print("events", len(EV), flush=True)
def sleeve(H):
    pos = pd.DataFrame(0.0, index=idx, columns=[e[0] for e in EV]); R = pos.copy(); F = pos.copy(); fwd = []
    for s, t0, c, fr in EV:
        start = (t0 + pd.Timedelta(hours=24)).ceil("D"); stop = min(start + pd.Timedelta(days=H), c.index.max())
        if start >= stop or start > idx[-1]:
            continue
        m = (idx >= start) & (idx < stop); pos.loc[m, s] = -0.05
        r = c.pct_change().shift(-1)                                   # return of the hour starting at t (close t -> close t+1)
        R[s] = r.reindex(idx).fillna(0.0); f = fr.copy(); f.index = f.index - pd.Timedelta(hours=1); F[s] = f.reindex(idx).fillna(0.0)
        if c.index.max() >= start + pd.Timedelta(days=30):
            fwd.append((start.year, float(c.asof(start + pd.Timedelta(days=30)) / c.asof(start) - 1)))
    g = pos.abs().sum(axis=1); pos = pos.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    pnl = (pos * R).sum(axis=1) - (pos * F).sum(axis=1) - pos.diff().abs().sum(axis=1).fillna(0.0) * 10 / 1e4
    return pnl, g, fwd
out = {"reference v9.5": [REF[0], REF[1]], "events": len(EV), "trials": {}}
for k, H in (("A hold 30 days", 30), ("B hold 7 days", 7)):
    s, g, fwd = sleeve(H); b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
    fw = pd.DataFrame(fwd, columns=["year", "r30"])
    out["trials"][k] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "mean gross": round(float(g.loc["2022":].mean()), 3),
                        "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3))),
                        "30-day return of listed coins (mean / median / n) by year": {str(y): [round(float(x.mean()), 3), round(float(x.median()), 3), int(len(x))] for y, x in fw.groupby("year")["r30"]}}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen425.json").write_text(json.dumps(out, indent=1))
