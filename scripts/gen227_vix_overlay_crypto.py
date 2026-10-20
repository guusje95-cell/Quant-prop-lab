"""Gen227 (config/gen227_protocol.json): VIX risk-off overlay on v7 and bf. Writes results/gen227.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(open(ROOT / "scripts/gen171_crypto_calendar.py").read().split("\ndays = pd.date_range")[0], g)
v7, sh, per = g["v7"], g["sh"], g["per"]
k = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], k)
bf = k["CS"].portfolio_v5(pd.concat([k["HB0"], (k["p6"]() + k["r1"](1e-4)).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
vix = pd.read_parquet(ROOT / "research_data/more2/vix_VIX.parquet")["close"]
hi = vix > vix.rolling(252, min_periods=200).quantile(0.8)
m = pd.Series(np.where(hi, 0.5, 1.0), index=vix.index).shift(1)              # known before day d starts (previous US close)
out = {}
for n, b in (("v7", v7), ("bf", bf)):
    md = m.reindex(pd.date_range(m.index.min(), b.index.max().normalize())).ffill()
    mult = md.reindex(b.index.floor("D")).set_axis(b.index).fillna(1.0)
    b1 = b * mult
    B0, k0 = sh(b, "2022-01-01", "2026-09-30"), per(b, "2022-01-01"); B1, k1 = sh(b1, "2022-01-01", "2026-09-30"), per(b1, "2022-01-01")
    out[n] = {"before": [round(B0, 3), np.round(k0, 3).tolist()], "after": [round(B1, 3), np.round(k1, 3).tolist()], "share of days halved": round(float((mult < 1).groupby(b.index.floor("D")).max().mean()), 2),
              "pass": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
    print(n, out[n], flush=True)
json.dump(out, open(ROOT / "results/gen227.json", "w"), indent=1)
