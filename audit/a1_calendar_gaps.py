"""Audit A1 (read-only): how does the V6 futures pipeline handle calendars, NaNs and gaps?
Checks (1) weekend/duplicate rows after the per-date `groupby(date).last()`, (2) returns spanning >1 business day,
(3) their share of total variance, (4) whether ewm(ignore_na=True) sigma differs from a business-day-resampled sigma
(pysystemtrade convention: resample('1B').last() then diff), (5) union-calendar NaN cells and how the engine treats them."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.data import futures_panel as FP
from qpl.backtesting import panel as PB

P = FP.build(); U, _ = FP.universe(P); ret = P["ret"][U]
out = {}
# (1) weekend dates in the union index and per instrument
idx = ret.index
out["union_rows"] = len(idx)
out["union_weekend_rows"] = int((idx.dayofweek >= 5).sum())
wk = ret[idx.dayofweek >= 5].notna().sum()
out["instruments_with_weekend_obs"] = int((wk > 0).sum())
out["weekend_obs_total"] = int(wk.sum())
out["weekend_obs_by_year"] = ret[idx.dayofweek >= 5].notna().sum(axis=1).groupby(idx[idx.dayofweek >= 5].year).sum().to_dict()
out["duplicate_index"] = int(idx.duplicated().sum())
# (2)/(3) gaps per instrument: business days between consecutive observations
rows = []
for c in U:
    s = ret[c].dropna()
    if len(s) < 300: continue
    bd = np.busday_count(s.index[:-1].values.astype("datetime64[D]"), s.index[1:].values.astype("datetime64[D]"))
    gap = pd.Series(np.r_[1, bd], index=s.index)
    multi = gap > 1
    rows.append({"inst": c, "n": len(s), "share_multi_bday": multi.mean(), "max_gap_bdays": int(gap.max()),
                 "var_share_multi": float((s[multi] ** 2).sum() / (s ** 2).sum()),
                 "ratio_absret_multi_vs_single": float(s[multi].abs().mean() / s[~multi].abs().mean()) if multi.any() else np.nan})
g = pd.DataFrame(rows).set_index("inst")
out["gap_summary"] = g.describe().round(3).to_dict()
out["worst_gap_instruments"] = g.sort_values("max_gap_bdays", ascending=False).head(8).round(3).to_dict("index")
# (4) sigma: V6 (ewm ignore_na on union calendar) vs pysystemtrade-like (resample 1B last, diff, ewm span 35)
s_v6 = PB.sigma(ret)
lp = (1 + ret.fillna(0)).cumprod().where(ret.notna().cumsum() > 0)
lp_b = lp.where(ret.notna()).resample("1B").last()
r_b = lp_b.pct_change(fill_method=None)
s_b = (r_b.ewm(span=35, min_periods=20, ignore_na=True).std() * np.sqrt(256)).reindex(idx, method="ffill")
ratio = (s_v6 / s_b).where(s_v6.notna() & s_b.notna())
out["sigma_ratio_v6_over_bday"] = {"median": float(np.nanmedian(ratio.values)), "p01": float(np.nanpercentile(ratio.values, 1)),
                                   "p99": float(np.nanpercentile(ratio.values, 99))}
# (5) union-calendar NaN cells after an instrument started (holidays / missing days)
started = ret.notna().cumsum() > 0
out["nan_cells_after_start_share"] = float((ret.isna() & started).values.sum() / started.values.sum())
import json; print(json.dumps(out, indent=1, default=str))
