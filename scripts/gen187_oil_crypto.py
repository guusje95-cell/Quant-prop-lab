"""Gen187 (config/gen187_protocol.json): oil predicts crypto, v7 sleeve. Writes results/gen187.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen171_crypto_calendar.py").read()
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(src.split("\ndays = pd.date_range")[0], g)
CS, HV7, sh, per, B0, k0 = (g[k] for k in ("CS", "HV7", "sh", "per", "B0", "k0"))
import futures_db as F
cl = (1 + F.daily("CL").r.fillna(0.0)).cumprod(); cl = cl[cl.index.weekday < 5]
s = cl / cl.shift(21) - 1; me = cl.index.to_series().groupby(cl.index.to_period("M")).max()
days = pd.date_range("2020-01-01", "2026-10-01"); w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for d in me:
    if d < days[0] or not np.isfinite(s.loc[d]) or s.loc[d] >= 0:
        continue
    nxt = (d + pd.offsets.MonthEnd(1)).normalize()
    w.loc[d:nxt - pd.Timedelta(days=1)] = 0.5                          # row d = decided at the close of d, held during d+1 .. month end
sl = CS._from_daily_weights(w, ["BTC", "ETH"], 7.5).loc[:"2026-09-30 23:00"]
p = per(sl, "2020-01-01"); vb = CS.portfolio_v5(pd.concat([HV7, sl.rename("oil timing")], axis=1).fillna(0.0))[0]
B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
out = {"v7": [round(B0, 3), np.round(k0, 3).tolist()], "sleeve D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen187.json", "w"), indent=1)
