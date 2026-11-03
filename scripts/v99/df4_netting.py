"""DF-4 (research/v99/df4_protocol.json): net execution of the daily-flat equity-index book. Writes results/v99/df4_netting.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat_positions as DP
F = DP.F
import fbook

EQ = DP.EQ8
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]
P = Q[Q.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0); T = P.loc[:"2022-12-31"]
w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
ref = (raw * lvl).dropna()
H = DP.hourly(DP.session_positions())
out_g, out_n = 0.0, 0.0
for r in DP.MK4:
    f = F.front(r); idx = f.index; td = F.trade_date(idx); et = F.ny(idx)
    k = pd.Series((lvl.reindex(td).fillna(0.0)).to_numpy(), index=idx)
    net = sum(H[n][r].reindex(idx).fillna(0.0) * w[n] for n in EQ if r in H[n]) * k
    net[(et.h == 16).to_numpy()] = 0.0                                     # flat from 16:00 ET
    gap_after = np.r_[np.diff(idx.asi8) / 3.6e12, np.inf] > 1.01
    net[gap_after] = 0.0 if False else net[gap_after]                      # (position into a closure is already 0: the 16:00 bar precedes it)
    c = F.cost_frac(r, f.close)
    gross = net * f.r.fillna(0.0)
    turn = net.diff().abs().fillna(net.abs())
    out_g = out_g + gross.groupby(td).sum(); out_n = out_n + (gross - turn * c).groupby(td).sum()
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
netb = out_n.reindex(ref.index).fillna(0.0)
res = {"research book (each sleeve pays its own costs)": per(ref), "net execution book": per(netb),
       "net execution, gross (no costs)": per(out_g.reindex(ref.index).fillna(0.0)),
       "annual cost drag research vs net (book units, 2023-26)": None}
grs = (P * w).sum(axis=1) * lvl
print(json.dumps(res, indent=1)); (ROOT / "results/v99/df4_netting.json").write_text(json.dumps(res, indent=1))
