"""DF-1c (research/v99/df1c_protocol.json). Writes results/v99/df1c.json and results/v99/df1c_sleeves.parquet."""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"; os.environ["QPL_DF_SIGNALS"] = "true"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat_positions as DP                                     # TRUE bars: signals
import futures_db as F
pos = DP.session_positions(); H = DP.hourly(pos); EQ = DP.EQ8
true_r = {r: F.front(r)[["r"]].copy() for r in DP.MK4}
import dailyflat
dailyflat.patch()                                                    # from here on: patched bars for the P&L
F.front.cache_clear()
per_sleeve, net_g, net_c = {}, {}, {}
for n in EQ:
    tot = 0.0
    for r in H[n].columns:
        f = F.front(r); idx = f.index; et = F.ny(idx); p = H[n][r].reindex(idx).fillna(0.0).copy()
        p[(et.h == 16).to_numpy()] = 0.0
        gap = np.r_[True, np.diff(idx.asi8) / 3.6e12 > 1.01]
        turn = p.diff().abs().fillna(p.abs()); turn[gap] = (p.abs() + p.shift(1).abs().fillna(0.0))[gap]
        tot = tot + (p * f.r.fillna(0.0) - turn * F.cost_frac(r, f.close)).groupby(F.trade_date(idx)).sum()
    per_sleeve[n] = tot
Q = pd.DataFrame(per_sleeve); Q = Q[Q.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
Q.to_parquet(ROOT / "results/v99/df1c_sleeves.parquet")
import fbook
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
old = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]
out = {"DF-3 (flawed: patched signals), per-sleeve costs": per(fbook.build(old)),
       "DF-1c corrected (true signals, daily-flat P&L), per-sleeve costs": per(fbook.build(Q)),
       "sleeves corrected": {c: per(Q[c]) for c in EQ}, "sleeves flawed": {c: per(old[c]) for c in EQ}}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df1c.json").write_text(json.dumps(out, indent=1))
