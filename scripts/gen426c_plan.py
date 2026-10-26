"""Gen426c (descriptive): v9.5 + Gen426 listing short (flagged candidate v9.6): planning Sharpe, tails, HyroTrader at planning level.
Writes results/gen426c.json and results/gen426_book_hourly.parquet."""
import json
import sys
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen426_listing_stop.py").read().split("\ns, g, n = sleeve(30)")[0]
g = {"__file__": str(ROOT / "scripts/gen426_listing_stop.py")}; exec(compile(src, "g426", "exec"), g)
sleeve, V, CS, unit, dd = (g[k] for k in ("sleeve", "V", "CS", "unit", "dd"))
from qpl.lab import propfirms as PF
src2 = open(ROOT / "scripts/gen90_books.py").read(); exec(src2[src2.index("def to_daily_stop"):src2.index("P = []")], globals())
END = "2026-09-30"; s = sleeve(30)[0]
books = {"v9.5": unit(CS.portfolio_v5(V)[0]), "v9.6 candidate": unit(CS.portfolio_v5(V.assign(**{"listing short": s}))[0])}
pd.DataFrame({"book": books["v9.6 candidate"], "listing short": s}).to_parquet(ROOT / "results/gen426_book_hourly.parquet")
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]; out = {}
for nm, b in books.items():
    d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std()
    pl = {}
    for N in (300, 1000, 1800):
        sr0 = np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e))); pl[f"N={N}"] = round(float((sr - sr0) * np.sqrt(365)), 3)
    x2 = b * 2.0; eq = (1 + dd(x2.loc["2022":])).cumprod()
    res = {"Sharpe": round(float(sr * np.sqrt(365)), 3), "planning": pl, "worst day at risk 2": round(float(dd(x2.loc["2022":]).min()), 4),
           "worst hour at risk 2": round(float(x2.loc["2022":].min()), 4), "max DD at risk 2": round(float((eq / eq.cummax() - 1).min()), 4)}
    for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
        x = unit(shift_to(b, pl["N=1800"])).loc[A:Z]; ch = to_daily_stop(x * 1.5, 0.5 * HY.daily_loss)
        paths, cal0 = PF._paths(pd.DataFrame(index=ch.index, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11); per_day = len(ch) / max(1, cal0[-1])
        r, lo, hi = PF._arrays(ch, 1.0); n = []
        for _, xx in paths:
            cal = (np.arange(len(xx)) / per_day).astype(int); n.append(PF._ledger(r[xx], lo[xx], hi[xx], r[xx], lo[xx], hi[xx], cal, 0, len(xx), HY, 5)["net"])
        n = np.array(n); res[f"HyroTrader 1.5/1.5 at planning N=1800, {win}"] = {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P_profit": round(float((n > 0).mean()), 3)}
    out[nm] = res; print(nm, json.dumps(res), flush=True)
(ROOT / "results/gen426c.json").write_text(json.dumps(out, indent=1))
