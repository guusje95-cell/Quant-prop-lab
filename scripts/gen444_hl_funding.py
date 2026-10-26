"""Gen444 (config/gen444_protocol.json): Hyperliquid funding signals across the 6 majors. Writes results/gen444.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, V0, B, C6, pnl, days = (g[k] for k in ("shp", "per", "unit", "CS", "V", "B", "C6", "pnl", "days"))
import listing_live as LL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def dly(s):                                                    # value of day d at row d + 1 (relative crowding convention)
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); return s.groupby(level=0).mean().reindex(days).shift(1)
HL, BN = {}, {}
for c in C6:
    h = pd.read_parquet(ROOT / f"research_data/hyperliquid/{c}_funding.parquet")["fundingRate"] * 8.0; h.index = pd.DatetimeIndex(h.index).floor("h")
    HL[c] = dly(h).rolling(7, min_periods=5).mean()
    f = B.funding(c); BN[c] = dly(f).rolling(7, min_periods=5).mean()
def rel(raw):
    Z = raw.apply(lambda s: z(s, 90)); Zd = Z.sub(Z.mean(axis=1), axis=0); return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
S = {"A Gen406 Y4 Hyperliquid funding relative": pnl(rel(pd.DataFrame(HL))).reindex(idx).fillna(0.0),
     "B venue funding spread relative": pnl(rel(pd.DataFrame(HL) - pd.DataFrame(BN))).reindex(idx).fillna(0.0)}
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "trials": {}}
for k, s in S.items():
    b = unit(CS.portfolio_v5(V6.assign(**{k: s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": [None if np.isnan(x) else x for x in per(s)], "by year": {str(y): shp(s, str(y), str(y)) for y in range(2023, 2027)},
                        "corr relative crowding": round(float(s.corr(V6["relative crowding 6"])), 2), "book": r,
                        "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen444.json").write_text(json.dumps(out, indent=1))
