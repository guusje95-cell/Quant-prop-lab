"""Gen437 (descriptive): two HyroTrader $200k accounts on v9.6 - started together vs the second 90 / 180 days later (same bootstrap
paths; each account trades 2 years). Planning level 1.59, sizing 1.5 / 1.5 / stop 0.5. Writes results/gen437.json."""
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
src_book = sys.argv[1] if len(sys.argv) > 1 else "results/gen426_book_hourly.parquet"
b = unit(pd.read_parquet(ROOT / src_book)["book"])
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]; out = {"book": src_book}
for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
    for lvl in (1.2, 1.59):
        x = unit(shift_to(b, lvl)).loc[A:Z]; ch = to_daily_stop(x * 1.5, 0.5 * HY.daily_loss)
        r, lo, hi = PF._arrays(ch, 1.0); cal_all = PF._days(ch.index); per_day = len(ch) / max(1, cal_all[-1])
        paths, _ = PF._paths(pd.DataFrame(index=ch.index, data={"net": 0.0}), "bootstrap", 730 + 180, 1, 400, 20, 11)
        res = {}
        for lag in (0, 90, 180):
            tot = []
            for _, xx in paths:
                n1 = int(730 * per_day); o = int(lag * per_day); nets = []
                for s0 in (0, o):
                    seg = xx[s0:s0 + n1]; cal = (np.arange(len(seg)) / per_day).astype(int)
                    nets.append(PF._ledger(r[seg], lo[seg], hi[seg], r[seg], lo[seg], hi[seg], cal, 0, len(seg), HY, 5)["net"])
                tot.append(sum(nets))
            t = np.array(tot); res[f"second account +{lag} days"] = {"mean": round(float(t.mean())), "p10": round(float(np.percentile(t, 10))), "P_total_loss": round(float((t < 0).mean()), 3)}
        out[f"{win} Sharpe {lvl}"] = res; print(win, lvl, json.dumps(res), flush=True)
(ROOT / "results/gen437.json").write_text(json.dumps(out, indent=1))
