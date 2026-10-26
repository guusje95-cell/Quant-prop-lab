"""Gen445 (config/gen445_protocol.json): the frozen cascade rule on the point-in-time top-50 (and the Gen410 top-20 for comparison).
Writes results/gen445.json (and results/gen410_pu.json with the top-20 run through the same helper)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen57_cascade_hourly as CH
import listing_live as LL
import pit_universe as PU
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
pack_frames = {c: CH.hourly(c).copy() for c in PU.PACK}
def cascade_on(n):
    mem = PU.members(n); CH.CACHE.clear(); missing = []
    for c in [c for c in mem.columns if mem[c].any()]:
        d = PU.frame(c)
        if d is None:
            missing.append(c); continue
        m = mem[c].reindex(d.index.floor("D")).fillna(False).to_numpy()
        d = d.copy(); d["oi"] = d["oi"].where(m); CH.CACHE[c] = d
    s = CS.cascade(limit=0.005, through=0.001, coins=list(CH.CACHE)).reindex(idx).fillna(0.0)
    CH.CACHE.clear(); CH.CACHE.update(pack_frames)
    return s, missing
res = {}
for n in (20, 50):
    s, miss = cascade_on(n); b = unit(CS.portfolio_v5(V6.assign(**{"cascade limit strict": s}))[0]); r = [shp(b), per(b)]
    res[n] = {"coins without data": miss, "sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book v9.6": r}
    print(n, res[n], flush=True)
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 A..Z (pack cascade)": [REF[0], REF[1]], "pack cascade sleeve": per(V6["cascade limit strict"]),
       "top-20 (Gen410 universe)": res[20], "top-50": res[50], "pass top-50": bool(ok(res[50]["book v9.6"], REF)),
       "Gen410 change vs pack (v9.6)": round(res[20]["book v9.6"][0] - REF[0], 3)}
(ROOT / "results/gen445.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("pass top-50", "Gen410 change vs pack (v9.6)")}))
