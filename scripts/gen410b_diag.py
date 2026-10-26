"""Gen410b (descriptive diagnostic): replication check of the point-in-time cascade machinery on the pack coins, and the trades
behind the point-in-time losses. Writes results/gen410b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen57_cascade_hourly as CH
import pit_universe as PU
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
pack_frames = {c: CH.hourly(c).copy() for c in PU.PACK}
# 1) replication: pack coins through PU.frame, no membership mask
CH.CACHE.clear()
for c in PU.PACK:
    CH.CACHE[c] = PU.frame(c)
rep = CS.cascade(limit=0.005, through=0.001, coins=PU.PACK).reindex(idx).fillna(0.0)
out = {"replication max |diff| vs saved pack sleeve": float((rep - V["cascade limit strict"]).abs().max()), "replication sleeve": per(rep)}
# 2) point-in-time top-20 per coin contribution
mem = PU.members(20); CH.CACHE.clear(); per_coin = {}
coins = [c for c in mem.columns if mem[c].any()]
for c in coins:
    d = PU.frame(c)
    if d is None:
        continue
    m = mem[c].reindex(d.index.floor("D")).fillna(False).to_numpy(); d = d.copy(); d["oi"] = d["oi"].where(m); CH.CACHE[c] = d
full = CS.cascade(limit=0.005, through=0.001, coins=list(CH.CACHE)).reindex(idx).fillna(0.0)
for c in list(CH.CACHE):                                 # leave-one-coin-out contribution
    others = [x for x in CH.CACHE if x != c]
    s = CS.cascade(limit=0.005, through=0.001, coins=others).reindex(idx).fillna(0.0)
    per_coin[c] = round(float((full - s).sum()), 4)
worst = sorted(per_coin.items(), key=lambda kv: kv[1])[:10]; best = sorted(per_coin.items(), key=lambda kv: -kv[1])[:5]
wd = dd(full).sort_values().head(8)
out.update({"pit sleeve": per(full), "pit total P&L": round(float(full.sum()), 3), "pack total P&L": round(float(V["cascade limit strict"].sum()), 3),
            "worst coins (marginal P&L)": worst, "best coins": best, "worst days": {str(k.date()): round(float(v), 4) for k, v in wd.items()},
            "pit sleeve without the 5 worst coins": None})
ex = [c for c in CH.CACHE if c not in dict(worst[:5])]
s5 = CS.cascade(limit=0.005, through=0.001, coins=ex).reindex(idx).fillna(0.0); out["pit sleeve without the 5 worst coins"] = per(s5)
CH.CACHE.clear(); CH.CACHE.update(pack_frames)
(ROOT / "results/gen410b.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
