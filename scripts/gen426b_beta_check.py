"""Gen426b (descriptive): is the Gen426 listing short more than short altcoin beta? Regress the daily sleeve on BTC and on an
equal-weight established-alt index (the 6 majors ex BTC), per period; and compare with a plain beta-matched short of that index
added to v9.5. Writes results/gen426b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen426_listing_stop.py").read().split("\ns, g, n = sleeve(30)")[0]
g = {"__file__": str(ROOT / "scripts/gen426_listing_stop.py")}; exec(compile(src, "g426", "exec"), g)
sleeve, V, CS, unit, shp, per, dd, REF = (g[k] for k in ("sleeve", "V", "CS", "unit", "shp", "per", "dd", "REF"))
from qpl.lab import binance_pack as B
s = sleeve(30)[0]; sd = dd(s)
px = pd.DataFrame({c: B.k5(c).close.resample("1D").last() for c in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")}).pct_change()
X = pd.DataFrame({"btc": px["BTC"], "alts": px.drop(columns="BTC").mean(axis=1)}).reindex(sd.index)
out = {"periods": {}}
for nm, (a, z) in {"2022": ("2022", "2022"), "2023-24": ("2023", "2024"), "2025-26": ("2025", "2026-09-30"), "all": ("2022", "2026-09-30")}.items():
    y = sd.loc[a:z]; x = X.loc[a:z].fillna(0.0); A = np.column_stack([np.ones(len(x)), x.values]); coef, *_ = np.linalg.lstsq(A, y.values, rcond=None)
    res = y.values - A[:, 1:] @ coef[1:]
    out["periods"][nm] = {"beta btc": round(float(coef[1]), 3), "beta alts": round(float(coef[2]), 3), "raw Sharpe": round(float(y.mean() / y.std() * np.sqrt(365)), 2),
                          "beta-hedged Sharpe": round(float(res.mean() / res.std() * np.sqrt(365)), 2), "corr with alts": round(float(np.corrcoef(y, x["alts"])[0, 1]), 2)}
# plain short of the alt index with the sleeve's full-sample beta, as a sleeve
coef_all = out["periods"]["all"]; bh = coef_all["beta alts"]
alts_h = pd.DataFrame({c: B.k5(c).close.resample("1h").last() for c in ("ETH", "SOL", "XRP", "BNB", "DOGE")}).pct_change().mean(axis=1).reindex(V.index).fillna(0.0)
plain = bh * alts_h
b1 = unit(CS.portfolio_v5(V.assign(**{"plain alt short": plain}))[0]); b2 = unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0])
hedged = s - plain; b3 = unit(CS.portfolio_v5(V.assign(**{"listing short beta-hedged": hedged}))[0])
out["books"] = {"v9.5": [REF[0], REF[1]], "+ plain alt short (same beta, no costs)": [shp(b1), per(b1)], "+ listing short (Gen426)": [shp(b2), per(b2)],
                "+ listing short beta-hedged": [shp(b3), per(b3)]}
out["beta-hedged sleeve"] = per(hedged)
(ROOT / "results/gen426b.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
