"""Gen443 (config/gen443_protocol.json): listing short entered 6 h after listing. Writes results/gen443.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); v96 = unit(CS.portfolio_v5(V.assign(**{"listing short": ls}))[0]); REF = (shp(v96), per(v96))
EVX = []
for s in LL.symbols():
    k, f = LL._read(s)
    if k is None or len(k) < 12:
        continue
    t0 = k.index.min()
    if t0 < LL.FIRST or k.loc[:t0 + pd.Timedelta(hours=5), "quote_volume"].sum() < 2.5e6:
        continue
    EVX.append((s, t0, k["close"], f))
def sleeve(cm):
    P = {}
    for s, t0, c, f in EVX:
        start = t0 + pd.Timedelta(hours=6); end = start + pd.Timedelta(days=30)
        cc = c.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * 1.30].index
        last = hit[0] if len(hit) else end - pd.Timedelta(hours=1)
        p = pd.Series(-0.05, index=c.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
        P[s[:-4]] = p.where(c.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
    Pdf = pd.DataFrame(P); g = Pdf.abs().sum(axis=1); Pdf = Pdf.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx); CF = {s[:-4]: (c, f) for s, t0, c, f in EVX}
    for n in Pdf.columns:
        c, f = CF[n]; p = Pdf[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 * cm / 1e4
    return out
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "events": len(EVX), "trials": {}}
for nm, cm in (("A early entry", 1.0), ("A early entry, costs x2", 2.0)):
    s = sleeve(cm); b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book": r, "strict rule": bool(ok(r, REF))}
    print(nm, out["trials"][nm], flush=True)
out["pass"] = bool(out["trials"]["A early entry"]["strict rule"] and all(out["trials"]["A early entry, costs x2"]["book"][1][i] >= REF[1][i] for i in range(3)))
(ROOT / "results/gen443.json").write_text(json.dumps(out, indent=1)); print("pass", out["pass"])
