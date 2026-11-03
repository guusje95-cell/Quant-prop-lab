"""F-CX2 (research/v99/fcx2_protocol.json). Writes results/v99/fcx2.json."""
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
S = fbook.sleeves(); S["CX"] = daily(g["execute"](g["SLEEVES"]["S6 C* BTC/ETH legs"], "a")).reindex(S.index).fillna(0.0)
S2 = S.copy(); S2["CXD"] = daily(g["execute"](g["SLEEVES"]["S2 deleveraging bounce"], "a")).reindex(S.index).fillna(0.0)
out = {"reference (with CX)": per(fbook.build(S)), "with CX + CXD": per(fbook.build(S2)), "CXD sleeve": per(S2["CXD"]),
       "corr CXD vs CX since 2020": round(float(S2.loc["2020":, "CXD"].corr(S2.loc["2020":, "CX"])), 3)}
out["pass"] = bool(out["with CX + CXD"][2] >= out["reference (with CX)"][2] + 0.05 and out["with CX + CXD"][1] >= out["reference (with CX)"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx2.json").write_text(json.dumps(out, indent=1))
