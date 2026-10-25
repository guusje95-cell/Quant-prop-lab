"""Gen380b (descriptive): prop dollars, drawdown and deflated planning Sharpe of K1 vs K1 + Gen380 basket. Writes results/gen380b.json."""
import json
import sys
from dataclasses import replace
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
base = pd.read_parquet(ROOT / "results/k1_sleeves.parquet"); bh = pd.read_parquet(ROOT / "results/gen380_basket_hourly.parquet")["basket"]
BOOK = {"K1": unit(CS.portfolio_v5(base)[0]), "K1 + basket": unit(CS.portfolio_v5(base.assign(**{"diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0])}
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
def prop(h, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * HY.daily_loss), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
out = {}
for k, b in BOOK.items():
    d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std(); g3, g4 = skew(d), kurtosis(d, fisher=False); N = 1650
    sr0 = np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e)))
    plan = round(float((sr - sr0) * np.sqrt(365)), 3); eq = (1 + 2.0 * d).cumprod()
    out[k] = {"Sharpe 2022-26": shp(b), "planning (N = 1,650)": plan, "max DD at risk 2.0": round(float((eq / eq.cummax() - 1).min()), 4), "worst day at risk 2.0": round(float(2 * d.min()), 4),
              "HyroTrader 2022-24": prop(b, "2022-01-01", "2024-12-31 23:00"), "HyroTrader 2025-26": prop(b, "2025-01-01", END + " 23:00"),
              "HyroTrader at planning level (2025-26 days)": prop(unit(shift_to(b, plan)), "2025-01-01", END + " 23:00")}
    print(k, out[k], flush=True)
(ROOT / "results/gen380b.json").write_text(json.dumps(out, indent=1))
