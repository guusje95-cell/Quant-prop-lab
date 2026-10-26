"""Gen436 (config/gen436_protocol.json): v9.6 listing short on the full A..Z point-in-time universe. Writes results/gen436.json."""
import json
import sys
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
v95 = unit(CS.portfolio_v5(V)[0]); R95 = (shp(v95), per(v95))
s, pos, EV = LL.pnl(idx); b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
syms = {x[0] for x in EV}
d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std()
plan = {f"N={N}": round(float((sr - np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e)))) * np.sqrt(365)), 3) for N in (300, 1000, 1800)}
ok = r[0] >= R95[0] + 0.05 and all(r[1][i] >= R95[1][i] for i in range(3))
out = {"v9.5": [R95[0], R95[1]], "events": len(EV), "events T..Z": sum(1 for x in syms if x[0] >= "T" or not x[0].isascii()),
       "sleeve": per(s), "sleeve by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book v9.6 (A..Z, live timing)": r,
       "planning": plan, "v9.6 stands (decision rule)": bool(ok)}
pd.DataFrame({"book": b, "listing short": s}).to_parquet(ROOT / "results/gen436_book_hourly.parquet")
(ROOT / "results/gen436.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
