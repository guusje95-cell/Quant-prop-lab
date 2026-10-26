"""Gen449 (config/gen449_protocol.json): drop Binance listings of coins already seasoned on Bybit. Writes results/gen449.json."""
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
ls, _, EV = LL.pnl(idx); v96 = unit(CS.portfolio_v5(V.assign(**{"listing short": ls}))[0]); REF = (shp(v96), per(v96))
by = {x["symbol"][:-4]: pd.to_datetime(x["launchTime"], unit="ms") for x in json.loads((ROOT / "research_data/bybit_listings/instruments.json").read_text())}
keep = [e for e in EV if not (e[0][:-4] in by and by[e[0][:-4]] <= e[1] - pd.Timedelta(days=60))]
pos = LL.positions(idx, keep); s = pd.Series(0.0, index=idx)
for sym, t0, c, f in keep:
    n = sym[:-4]
    if n not in pos:
        continue
    p = pos[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s = s + p * r - p * fu - p.diff().abs().fillna(p.abs()) * LL.COST_BP / 1e4
b = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "events": len(EV), "seasoned events dropped": len(EV) - len(keep), "sleeve": per(s), "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen449.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
