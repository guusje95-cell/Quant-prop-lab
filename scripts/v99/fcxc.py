"""F-CXc robustness of F-CX (0 trials). Writes results/v99/fcxc.json."""
import json
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
    return h.groupby(d + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")).sum()


per = lambda b: [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3), round(F.sharpe(b, *fbook.JUDGE), 3)]
S = fbook.sleeves(); tgt = g["SLEEVES"]["S6 C* BTC/ETH legs"]; out = {"reference": per(fbook.build(S))}
def book(h):
    S2 = S.copy(); S2["CX"] = daily(h).reindex(S.index).fillna(0.0); return {"book": per(fbook.build(S2)), "sleeve": per(S2["CX"])}
ha = g["execute"](tgt, "a")
out["registered corrected (a)"] = book(ha)
out["weekend-flat (b)"] = book(g["execute"](tgt, "b"))
out["BTC only"] = book(g["execute"](tgt.assign(ETH=0.0), "a"))
out["ETH only"] = book(g["execute"](tgt.assign(BTC=0.0), "a"))
out["lagged 24h"] = book(g["execute"](tgt.shift(24).fillna(0.0), "a"))
dd = daily(ha); out["sleeve by year"] = {str(y): round(float(dd[dd.index.year == y].mean() / dd[dd.index.year == y].std() * np.sqrt(252)), 2) for y in range(2018, 2027) if dd[dd.index.year == y].std() > 0}
v = ["weekend-flat (b)", "BTC only", "ETH only", "lagged 24h"]
out["variants passing"] = sum(out[k]["book"][2] >= out["reference"][2] + 0.05 for k in v)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcxc.json").write_text(json.dumps(out, indent=1))
