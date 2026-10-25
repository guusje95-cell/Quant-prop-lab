"""Gen387 (config/gen387_protocol.json). Writes results/gen387.json."""
import json
import sys
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"; HY = PF.PRESETS["HyroTrader Two-Step $200k"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
b = pd.read_parquet(ROOT / "results/gen385_book_hourly.parquet")["book"]
d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std(); N = 1680
sr0 = np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e))); plan = float((sr - sr0) * np.sqrt(365))
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
pl = unit(shift_to(b, plan))
def prop(h, a, z, rc, rf):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * rc, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * rf, 0.5 * HY.daily_loss), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
G = {}
for rc in (2.0, 2.5, 3.0):
    for rf in (1.5, 2.0, 2.5):
        G[f"{rc}/{rf}"] = {"planning": prop(pl, "2025-01-01", END + " 23:00", rc, rf), "backtest 2022-24": prop(b, "2022-01-01", "2024-12-31 23:00", rc, rf), "backtest 2025-26": prop(b, "2025-01-01", END + " 23:00", rc, rf)}
        print(rc, rf, G[f"{rc}/{rf}"], flush=True)
cur = G["2.0/1.5"]["planning"]
ok = {k: v for k, v in G.items() if v["planning"]["P_profit"] >= 0.80 and v["planning"]["p10"] >= cur["p10"] - 2000}
best = max(ok, key=lambda k: ok[k]["planning"]["net"]); adopt = best != "2.0/1.5" and ok[best]["planning"]["net"] >= cur["net"] + 3000
out = {"planning Sharpe (N = 1,680)": round(plan, 3), "grid": G, "best eligible": best, "adopted": adopt}
(ROOT / "results/gen387.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: v for k, v in out.items() if k != "grid"}))
