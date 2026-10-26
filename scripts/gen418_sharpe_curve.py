"""Gen418 (descriptive): what live Sharpe does a prop account need? v9.5 shifted to live Sharpe 0.5..3.0, HyroTrader $200k,
challenge 1.5 / funded 1.5 / stop 0.5, both bootstrap windows (400 paths, block 20). Writes results/gen418.json."""
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
b = unit(pd.read_parquet(ROOT / "results/gen404_book_hourly.parquet")["book"])
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]; out = {}
for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
    for lvl in (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
        x = unit(shift_to(b, lvl)).loc[A:Z]; ch = to_daily_stop(x * 1.5, 0.5 * HY.daily_loss); idx = ch.index
        paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11); per_day = len(idx) / max(1, cal0[-1])
        r, lo, hi = PF._arrays(ch, 1.0); n = []; ps = []; br = []
        for _, xx in paths:
            cal = (np.arange(len(xx)) / per_day).astype(int); L = PF._ledger(r[xx], lo[xx], hi[xx], r[xx], lo[xx], hi[xx], cal, 0, len(xx), HY, 5)
            n.append(L["net"]); ps.append(L["passed"] > 0); br.append(L["breaches"])
        n = np.array(n); out[f"{win} live {lvl}"] = {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "median": round(float(np.median(n))),
                                                      "P_profit": round(float((n > 0).mean()), 3), "P_funded": round(float(np.mean(ps)), 3), "funded breaches": round(float(np.mean(br)), 2)}
        print(win, lvl, out[f"{win} live {lvl}"], flush=True)
(ROOT / "results/gen418.json").write_text(json.dumps(out, indent=1))
