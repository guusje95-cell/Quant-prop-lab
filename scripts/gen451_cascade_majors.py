"""Gen451 (config/gen451_protocol.json): cascade on BTC / ETH / SOL only vs v9.6 without cascade. Writes results/gen451.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
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
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V6.drop(columns="cascade limit strict"))[0]); REF = (shp(ref), per(ref))
s = CS.cascade(limit=0.005, through=0.001, coins=["BTC", "ETH", "SOL"]).reindex(idx).fillna(0.0)
b = unit(CS.portfolio_v5(V6.assign(**{"cascade limit strict": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.6 without cascade": [REF[0], REF[1]], "cascade BTC/ETH/SOL sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)},
       "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen451.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
