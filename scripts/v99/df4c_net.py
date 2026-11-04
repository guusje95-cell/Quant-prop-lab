"""DF-4c (execution, 0 trials): net execution of the corrected daily-flat equity book (DF-1c: true-price signals, daily-flat P&L).
Writes results/v99/df4c_net.json."""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"; os.environ["QPL_DF_SIGNALS"] = "true"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat_positions as DP
import futures_db as F
pos = DP.session_positions(); H = DP.hourly(pos); EQ = DP.EQ8
import dailyflat
dailyflat.patch()
Q = pd.read_parquet(ROOT / "results/v99/df1c_sleeves.parquet")[EQ]; T = Q.loc[:"2022-12-31"]
w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
raw = (Q * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); ref = (raw * lvl).dropna()
tot = 0.0
for r in DP.MK4:
    f = F.front(r); idx = f.index; td = F.trade_date(idx); et = F.ny(idx)
    k = pd.Series(lvl.reindex(td).fillna(0.0).to_numpy(), index=idx)
    net = sum(H[n][r].reindex(idx).fillna(0.0) * w[n] for n in EQ if r in H[n]) * k
    net[(et.h == 16).to_numpy()] = 0.0
    gap = np.r_[True, np.diff(idx.asi8) / 3.6e12 > 1.01]
    turn = net.diff().abs().fillna(net.abs()); turn[gap] = (net.abs() + net.shift(1).abs().fillna(0.0))[gap]
    tot = (tot if isinstance(tot, pd.Series) else pd.Series(dtype=float)).add((net * f.r.fillna(0.0) - turn * F.cost_frac(r, f.close)).groupby(td).sum(), fill_value=0.0)   # markets start at different dates (RTY 2017): no NaN days
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out = {"DF-1c research book (per-sleeve costs)": per(ref), "DF-4c net execution": per(tot.reindex(ref.index).fillna(0.0))}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df4c_net.json").write_text(json.dumps(out, indent=1))
