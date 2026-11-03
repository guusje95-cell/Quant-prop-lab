"""F-CX correction (0 trials): the registered daily sum dropped CME's Sunday-evening bars (UTC Sunday), i.e. the weekend gap P&L.
Here Saturday / Sunday P&L is booked on the next Monday; plus 2x costs and a by-year view. Writes results/v99/fcx_check.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
import fbook
import futures_db as F


def daily(h):
    d = h.index.floor("D"); wd = d.weekday
    d = d + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    return h.groupby(d).sum()


S = fbook.sleeves(); b0 = fbook.build(S)
per = lambda b: [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3), round(F.sharpe(b, *fbook.JUDGE), 3)]
out = {"reference": per(b0)}
tgt = g["SLEEVES"]["S6 C* BTC/ETH legs"]
h = g["execute"](tgt, "a"); out["weekend P&L share of CX total"] = round(float(h[h.index.weekday >= 5].sum() / h.sum()), 3)
for name, hh in (("CX weekend gap on Monday", h),):
    S2 = S.copy(); S2["CX"] = daily(hh).reindex(S2.index).fillna(0.0); b1 = fbook.build(S2)
    out[name] = {"book": per(b1), "sleeve": per(S2["CX"]), "by year book": {str(y): round(float(b1[b1.index.year == y].mean() / b1[b1.index.year == y].std() * np.sqrt(252)), 2) for y in range(2018, 2027)},
                 "by year ref": {str(y): round(float(b0[b0.index.year == y].mean() / b0[b0.index.year == y].std() * np.sqrt(252)), 2) for y in range(2018, 2027)}}
# 2x CME costs
orig = F.cost_frac; F.cost_frac = lambda c, px: 2 * orig(c, px)
h2 = g["execute"](tgt, "a"); F.cost_frac = orig
S2 = S.copy(); S2["CX"] = daily(h2).reindex(S2.index).fillna(0.0); out["CX at 2x costs"] = {"book": per(fbook.build(S2)), "sleeve": per(S2["CX"])}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx_check.json").write_text(json.dumps(out, indent=1))
