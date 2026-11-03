"""F-CX3 (research/v99/fcx3_protocol.json). Writes results/v99/fcx3.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
k = {"__file__": str(ROOT / "scripts/gen105_demand.py"), "__name__": "gen105"}
exec((ROOT / "scripts/gen105_demand.py").read_text().split("idx1 = IDX.append")[0], k)
import futures_db as F
from qpl.live.futures_cx import book, daily

per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); P["CX"] = pd.read_parquet(ROOT / "results/v99/cx_sleeve_prefix.parquet")["CX"].reindex(P.index).fillna(0.0)
h = g["execute"](g["d2h"](k["w"]), "a"); P2 = P.copy(); P2["CXK"] = daily(h).reindex(P.index).fillna(0.0)
out = {"reference (with CX)": per(book(P)[0]), "with CX + CXK": per(book(P2)[0]), "CXK sleeve": per(P2["CXK"]),
       "corr CXK vs CX since 2020": round(float(P2.loc["2020":, "CXK"].corr(P2.loc["2020":, "CX"])), 3),
       "CXK sleeve by year": {str(y): round(float(P2.CXK[P2.index.year == y].mean() / P2.CXK[P2.index.year == y].std() * np.sqrt(252)), 2) for y in range(2019, 2027) if P2.CXK[P2.index.year == y].std() > 0}}
out["pass"] = bool(out["with CX + CXK"][2] >= out["reference (with CX)"][2] + 0.05 and out["with CX + CXK"][1] >= out["reference (with CX)"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx3.json").write_text(json.dumps(out, indent=1))
