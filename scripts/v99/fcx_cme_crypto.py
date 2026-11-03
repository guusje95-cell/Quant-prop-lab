"""F-CX (research/v99/fcx_protocol.json): CME C* BTC/ETH legs as a futures-book sleeve. Writes results/v99/fcx.json."""
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

h = g["execute"](g["SLEEVES"]["S6 C* BTC/ETH legs"], "a")
cx = h.groupby(h.index.floor("D")).sum()
S = fbook.sleeves(); b0 = fbook.build(S); S2 = S.copy(); S2["CX"] = cx.reindex(S2.index).fillna(0.0); b1 = fbook.build(S2)
per = lambda b: [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3), round(F.sharpe(b, *fbook.JUDGE), 3)]
c = S2.loc["2018":].corrwith(S2.loc["2018":, "CX"]).round(2).drop("CX")
out = {"reference": per(b0), "with CX": per(b1), "CX stand-alone (daily, weekdays)": per(S2["CX"].replace(0, np.nan).fillna(0.0)),
       "max |corr| CX vs sleeves since 2018": float(c.abs().max()), "corr CX vs reference book": round(float(S2["CX"].reindex(b0.index).loc["2018":].corr(b0.loc["2018":])), 3)}
out["pass"] = bool(out["with CX"][2] >= out["reference"][2] + 0.05 and out["with CX"][1] >= out["reference"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx.json").write_text(json.dumps(out, indent=1))
