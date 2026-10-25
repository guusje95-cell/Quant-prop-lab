"""Gen397b (descriptive): v9.4 candidate (v9.3 + 6-coin relative crowding sleeve) - planning Sharpe, tail, prop, robustness of the book. Writes results/gen397b.json."""
import json
import sys
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, REF, sleeve = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "REF", "sleeve"))
from qpl.lab import propfirms as PF
s9 = open(ROOT / "scripts/gen90_books.py").read(); exec(s9[s9.index("def to_daily_stop"):s9.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")
def book(rc):
    return unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": rc}))[0])
def prop(h, a, z_):
    x = h.loc[a:z_]; pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * HY.daily_loss), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
def plan(b, N=1720):
    d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std()
    sr0 = np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e))); return round(float((sr - sr0) * np.sqrt(365)), 3)
v93 = unit(CS.portfolio_v5(V)[0]); b = book(sleeve(C6))
out = {}
for k, x in (("v9.3", v93), ("v9.4 candidate", b)):
    d = dd(x).loc["2022":END]; eq = (1 + 2 * d).cumprod()
    out[k] = {"Sharpe": [shp(x), per(x)], "planning (N = 1,720)": plan(x), "worst day at risk 2": round(float(2 * d.min()), 4), "max DD at risk 2": round(float((eq / eq.cummax() - 1).min()), 4),
              "HyroTrader 2022-24": prop(x, "2022-01-01", "2024-12-31 23:00"), "HyroTrader 2025-26": prop(x, "2025-01-01", END + " 23:00")}
    print(k, out[k], flush=True)
out["book robustness (sleeve variant -> book 2022-26 [periods])"] = {nm: [shp(bb := book(s)), per(bb)] for nm, s in (("costs x2", sleeve(C6, cm=2.0)), ("one day later", sleeve(C6, lag=1)), ("z 60", sleeve(C6, win=60)), ("z 180", sleeve(C6, win=180)))}
print(out["book robustness (sleeve variant -> book 2022-26 [periods])"])
(ROOT / "results/gen397b.json").write_text(json.dumps(out, indent=1))
