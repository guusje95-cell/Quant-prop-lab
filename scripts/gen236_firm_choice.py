"""Gen236 (config/gen236_protocol.json): firm / account / settings choice, nested. Writes results/gen236.json."""
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(open(ROOT / "scripts/gen171_crypto_calendar.py").read().split("\ndays = pd.date_range")[0], g)
bf = pd.read_parquet(ROOT / "results/gen234_book.parquet")["book"]
PR = PF.PRESETS
SF = lambda name: replace(PR[name], fee=PR[name].fee + 96.0)
BOOKS = {"v7": (g["v7"], {n: PR[n] for n in ["HyroTrader Two-Step $100k", "HyroTrader Two-Step $200k", "HyroTrader One-Step $100k", "Crypto Fund Trader 2-Phase $100k",
                                             "Crypto Fund Trader 2-Phase $100k + weekly payouts + 90% split", "Breakout Two-Step $100k"]}, "HyroTrader Two-Step $100k"),
         "bf": (bf, {"BrightFunded Two-Step Classic $100k": SF("BrightFunded Two-Step Classic $100k"), "BrightFunded Two-Step Bright $100k": SF("BrightFunded Two-Step Bright $100k"),
                     "FundedNext Stellar 2-Step $100k swap-free": PR["FundedNext Stellar 2-Step $100k swap-free"]}, "BrightFunded Two-Step Classic $100k")}


def run(h, f, sc, sf, a, z, halve=False):
    x = h.loc[a:z]; x = x - 0.5 * x.mean() if halve else x
    pb = PF.pipeline(to_daily_stop(x * sc, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * sf, 0.5 * f.daily_loss), horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


out = {}
for bn, (hb, firms, cur) in BOOKS.items():
    h = hb.loc["2022-01-01":"2026-09-30 23:00"]; dd = h.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum(); h = h * 0.15 / (dd.std() * np.sqrt(365))
    best = {}
    for fn, f in firms.items():
        rows = [{"sc": sc, "sf": sf, **run(h, f, sc, sf, "2022-01-01", "2024-12-31 23:00")} for sc, sf in itertools.product((1.0, 1.5, 2.0), (1.0, 1.5))]
        T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; r = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
        best[fn] = {"sc": float(r.sc), "sf": float(r.sf), "net 2022-24": int(r.net), "P 2022-24": float(r.P_profit)}; print(bn, fn, best[fn], flush=True)
    chf = max(best, key=lambda k: best[k]["net 2022-24"]); c = best[chf]
    res = {"per firm (2022-24)": best, "chosen firm": chf,
           "2025-26 chosen": run(h, firms[chf], c["sc"], c["sf"], "2025-01-01", "2026-09-30 23:00"),
           "2025-26 current": run(h, firms[cur], 2.0, 1.5, "2025-01-01", "2026-09-30 23:00"),
           "half-mean chosen": run(h, firms[chf], c["sc"], c["sf"], "2025-01-01", "2026-09-30 23:00", True),
           "half-mean current": run(h, firms[cur], 2.0, 1.5, "2025-01-01", "2026-09-30 23:00", True)}
    res["adopt"] = bool(chf != cur and res["2025-26 chosen"]["net"] > res["2025-26 current"]["net"] and res["2025-26 chosen"]["P_profit"] >= res["2025-26 current"]["P_profit"] - 0.02)
    out[bn] = res
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen236.json", "w"), indent=1)
