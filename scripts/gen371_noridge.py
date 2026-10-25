"""Gen371 (config/gen371_protocol.json): v8.6 with vs without the ridge ML sleeve. Writes results/gen371.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
H = pd.read_parquet(sys.argv[1]).drop(columns="port").loc[:"2026-09-30 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
A = unit(CS.portfolio_v5(H)[0]); Bx = unit(CS.portfolio_v5(H.drop(columns="ridge ML"))[0])
ref = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"]
sh = lambda h, a, z: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
mdd = lambda h, a, z: round(float(((1 + dd(h.loc[a:z]) * 2.0).cumprod() / (1 + dd(h.loc[a:z]) * 2.0).cumprod().cummax() - 1).min()), 4)
HY = PF.PRESETS["HyroTrader Two-Step $200k"]


def prop(h, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * HY.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "days_to_funded": pb["days_to_funded_median"]}


out = {"check A == cache_v86 (corr)": round(float(pd.concat([A, ref], axis=1).dropna().corr().iloc[0, 1]), 6)}
for k, h in (("A v8.6", A), ("B no ridge", Bx)):
    out[k] = {"Sharpe 2022 / 2023-24 / 2022-24": [sh(h, "2022", "2022"), sh(h, "2023", "2024"), sh(h, "2022", "2024")],
              "Sharpe 2025-26 (holdout, once)": sh(h, "2025", "2026-09-30"), "max DD at risk 2, 2022-24 / 2025-26": [mdd(h, "2022", "2024"), mdd(h, "2025", "2026-09-30")],
              "HyroTrader prop 2022-24": prop(h, "2022-01-01", "2024-12-31 23:00"), "HyroTrader prop 2025-26 (holdout)": prop(h, "2025-01-01", "2026-09-30 23:00")}
r = dd(H["ridge ML"]); out["ridge ML sleeve Sharpe by year"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in r.loc["2022":].groupby(r.loc["2022":].index.year)}
out["corr ridge vs rest of book (daily, 2022-26)"] = round(float(pd.concat([r, dd(Bx)], axis=1).loc["2022":].corr().iloc[0, 1]), 3)
w4 = r.loc["2022":].rolling(4).sum()
out["ridge: share of 4-day windows at or below -3.7% unit (paper so far)"] = round(float((w4 <= -0.037).mean()), 3)
a, b = out["A v8.6"], out["B no ridge"]
s_a, s_b = a["Sharpe 2022 / 2023-24 / 2022-24"], b["Sharpe 2022 / 2023-24 / 2022-24"]
pa, pbb = a["HyroTrader prop 2022-24"], b["HyroTrader prop 2022-24"]
out["B passes"] = bool(s_b[2] >= s_a[2] + 0.05 and s_b[0] >= s_a[0] and s_b[1] >= s_a[1] and pbb["net"] > pa["net"] and pbb["p10"] >= pa["p10"])
(ROOT / "results/gen371.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
