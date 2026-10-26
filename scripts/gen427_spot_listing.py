"""Gen427 (config/gen427_protocol.json): short after a later Binance spot listing. Writes results/gen427.json."""
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
LL.CAP = 1e9                                                     # uncapped positions; the cap is applied below on the combined book
EV = LL.events(); P1 = LL.positions(idx, EV)
SP = json.loads((ROOT / "research_data/binance_spot_listing_dates.json").read_text())
EV2, CF = [], {}
for s in LL.symbols():
    if s not in SP:
        continue
    c, f = LL._read(s)
    if c is None or len(c) == 0:
        continue
    d = pd.Timestamp(SP[s]["first_spot_file"]); t0 = c.index.min()
    if d >= pd.Timestamp("2021-06-01") and d >= t0 + pd.Timedelta(days=3):
        EV2.append((s, d, c["close"], f))
for s, t0, c, f in EV + EV2:
    CF[s[:-4]] = (c, f)
P2 = LL.positions(idx, EV2)
def cap(P):
    g = P.abs().sum(axis=1); return P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
def pnl(P):
    out = pd.Series(0.0, index=idx)
    for n in P.columns:
        c, f = CF[n]; p = P[n]
        r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * LL.COST_BP / 1e4
    return out
ls = pnl(cap(P1)); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
A = pnl(cap(P2)); bA = unit(CS.portfolio_v5(V6.assign(**{"spot-listing short": A}))[0]); rA = [shp(bA), per(bA)]
M = pd.concat([P1, P2], axis=1).T.groupby(level=0).min().T.reindex(idx).fillna(0.0); Bm = pnl(cap(M))
bB = unit(CS.portfolio_v5(V.assign(**{"listing short": Bm}))[0]); rB = [shp(bB), per(bB)]
REF_R = (3.161, [2.775, 3.919, 2.576])
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing, this code)": [REF[0], REF[1]], "spot events": len(EV2),
       "spot events per year": pd.Series([e[1].year for e in EV2]).value_counts().sort_index().to_dict(),
       "A spot-listing short as its own sleeve": {"sleeve": per(A), "corr listing short": round(float(dd(A).corr(dd(ls))), 2), "book": rA, "pass": bool(ok(rA, REF_R)), "pass vs live-timing reference too": bool(ok(rA, REF))},
       "B merged into the listing short": {"sleeve": per(Bm), "book": rB, "pass": bool(ok(rB, REF_R)), "pass vs live-timing reference too": bool(ok(rB, REF))}}
out["spot events per year"] = {str(k): int(v) for k, v in out["spot events per year"].items()}
(ROOT / "results/gen427.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
