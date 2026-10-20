"""Gen186 (config/gen186_protocol.json): oil-predicts-stocks in the merged bf index sleeve. Writes results/gen186.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen147_cfd_r1.py")}; exec(open(ROOT / "scripts/gen147_cfd_r1.py").read().split("P6 = p6()")[0], g)
CS, HB0, per, sh, IDXbf, p6, r1, hourly = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "p6", "r1", "hourly"))
w = hourly("WTI")["close"]; wd = w.groupby(w.index.floor("D")).last(); wd = wd[wd.index.weekday < 5]
sig = (wd / wd.shift(21) - 1)
me = wd.index.to_series().groupby(wd.index.to_period("M")).max()
pos = pd.Series(np.nan, index=wd.index)
for d in me:
    pos.loc[d] = 1.0 if sig.loc[d] < 0 else 0.0
pos = pos.ffill().fillna(0.0)                                                   # decided at the month-end daily close (UTC)
legs = []
for s in ("US100", "US500"):
    r = hourly(s)["close"].reindex(IDXbf).ffill(limit=72).pct_change().fillna(0.0)
    wh = (0.5 * pos).reindex(pd.date_range(pos.index.min(), IDXbf.max().floor("D"))).ffill().shift(1).reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
    legs.append(wh * r - wh.diff().abs().fillna(0.0) * 1e-4)
OIL = sum(legs); P6 = p6(); R1 = r1(1e-4)
ref = CS.portfolio_v5(pd.concat([HB0, (P6 + R1).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B0, k0 = sh(ref, "2022-01-01", "2026-09-30"), per(ref, "2022-01-01")
vb = CS.portfolio_v5(pd.concat([HB0, (P6 + R1 + OIL).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01"); p = per(OIL, "2020-01-01")
out = {"reference": [round(B0, 3), np.round(k0, 3).tolist()], "OIL leg D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen186.json", "w"), indent=1)
if out["pass"]:
    vb.to_frame("book").to_parquet(ROOT / "results/gen186_book.parquet")
