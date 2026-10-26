"""Gen430 (descriptive decision tool): HyroTrader $200k sizing grid for v9.6 (results/gen426_book_hourly.parquet) at planning-level Sharpe 1.59, a weak 1.2 and backtest, both windows. Writes results/gen430.json.
Same engine as scripts/plan_v95.py (block bootstrap, 400 paths, block 20, seed 11)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(pd.read_parquet(ROOT / "results/gen426_book_hourly.parquet")["book"])
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
GRID = [(c, f, s) for c in (1.0, 1.5, 2.0, 2.5) for f in (1.0, 1.5, 2.0, 2.5) for s in (0.5,)]
out = {}
for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
  for lvl in (1.2, 1.59, None):
    x = (b if lvl is None else unit(shift_to(b, lvl))).loc[A:Z]; res = {}
    for sc, sf, st in GRID:
        ch, fd = to_daily_stop(x * sc, st * HY.daily_loss), to_daily_stop(x * sf, st * HY.daily_loss)
        idx = ch.index.intersection(fd.index)
        paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11); per_day = len(idx) / max(1, cal0[-1])
        rc, loc, hic = PF._arrays(ch.reindex(idx).fillna(0.0), 1.0); rf, lof, hif = PF._arrays(fd.reindex(idx).fillna(0.0), 1.0); nets = []
        for _, xx in paths:
            cal = (np.arange(len(xx)) / per_day).astype(int)
            nets.append(PF._ledger(rc[xx], loc[xx], hic[xx], rf[xx], lof[xx], hif[xx], cal, 0, len(xx), HY, 5)["net"])
        n = np.array(nets); res[f"{sc}/{sf}"] = {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "median": round(float(np.median(n))), "P_profit": round(float((n > 0).mean()), 3)}
    k = win + " " + ("backtest" if lvl is None else f"Sharpe {lvl}"); out[k] = res; print(k, json.dumps(res), flush=True)
(ROOT / "results/gen430.json").write_text(json.dumps(out, indent=1))
