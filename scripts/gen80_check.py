"""Gen80 robustness for premium carry on 20 + extra coins (report only; no re-tuning): v5 swap (the registered book), per year,
2x costs, leave-one-coin-out over the top contributors, the strict Gen105 book rule. Writes results/gen80_check.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen80_112_breadth.py")}
exec(open(ROOT / "scripts/gen80_112_breadth.py").read().split("ref = book(")[0], g)
CS, H6, per, sh, perp_daily, prem_w, PACK, XS, HC = (g[k] for k in ("CS", "H6", "per", "sh", "perp_daily", "prem_w", "PACK", "XS", "HC"))
ALL = PACK + XS; out = {}
w20, wall = prem_w(PACK), prem_w(ALL)
p20, pall = perp_daily(w20, PACK), perp_daily(wall, ALL)
H5 = H6.drop(columns=["delev bounce"])
for nm, H in (("v5", H5), ("v6", H6)):
    b0 = CS.portfolio_v5(H)[0]; H1 = H.copy(); H1["premium carry"] = pall.reindex(H.index).fillna(0.0); b1 = CS.portfolio_v5(H1)[0]
    out[nm] = {"before 2022-26": round(sh(b0, "2022-01-01", "2026-09-30"), 3), "after": round(sh(b1, "2022-01-01", "2026-09-30"), 3),
               "before D/T/H": np.round(per(b0, "2022-01-01"), 3).tolist(), "after D/T/H": np.round(per(b1, "2022-01-01"), 3).tolist()}
yr = lambda p: {int(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in p.groupby(p.index.floor("D")).sum().groupby(lambda d: d.year)}
out["sleeve by year 20"] = yr(p20); out["sleeve by year all"] = yr(pall)
p2x = perp_daily(wall, ALL, cost=10); out["2x cost all D/T/H"] = np.round(per(p2x, "2020-01-01"), 3).tolist()
out["20 coins 2x cost D/T/H"] = np.round(per(perp_daily(w20, PACK, cost=10), "2020-01-01"), 3).tolist()
# contribution per coin (2023-26) and leave-one-out on the top 5
H = HC[ALL]; r = H.pct_change(fill_method=None).fillna(0.0)
wd = wall.reindex(wall.index.append(pd.DatetimeIndex([wall.index[-1] + pd.Timedelta(days=1)]))).shift(1)
held = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0)
contrib = (held * r).loc["2023":].sum().sort_values(ascending=False)
out["top contributors 2023-26 (sum of returns)"] = contrib.head(8).round(3).to_dict()
out["bottom contributors"] = contrib.tail(5).round(3).to_dict()
loo = {}
for c in contrib.head(5).index:
    cs = [x for x in ALL if x != c]; p = perp_daily(prem_w(cs), cs); loo[c] = np.round(per(p, "2020-01-01"), 3).tolist()
out["leave-one-out D/T/H"] = loo
print(json.dumps(out, indent=1))
json.dump(out, open(ROOT / "results/gen80_check.json", "w"), indent=1)
