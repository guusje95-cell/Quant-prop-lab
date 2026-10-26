"""Gen415 (descriptive decision tool): funded payout buffer for v9.5 at HyroTrader $200k (challenge 1.5 / funded 1.5 / stop 0.5).
Keep b of the account above the start at each payout (b = 0 is the current rule). Net is shown without and with the unpaid
profit at the horizon end (that money is still in the account). Writes results/gen415.json."""
import json
import sys
from dataclasses import replace
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
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
out = {}
for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
    for lvl in (1.0, 1.41, None):
        x = (b if lvl is None else unit(shift_to(b, lvl))).loc[A:Z]
        ch, fd = to_daily_stop(x * 1.5, 0.5 * HY.daily_loss), to_daily_stop(x * 1.5, 0.5 * HY.daily_loss); idx = ch.index.intersection(fd.index)
        paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11); per_day = len(idx) / max(1, cal0[-1])
        rc, loc, hic = PF._arrays(ch.reindex(idx).fillna(0.0), 1.0); rf, lof, hif = PF._arrays(fd.reindex(idx).fillna(0.0), 1.0); res = {}
        for buf in (0.0, 0.01, 0.02, 0.03, 0.05):
            for cop in (False, True):
                f = replace(HY, payout_buffer=buf, count_open_profit=cop); nets = []; br = []
                for _, xx in paths:
                    cal = (np.arange(len(xx)) / per_day).astype(int); L = PF._ledger(rc[xx], loc[xx], hic[xx], rf[xx], lof[xx], hif[xx], cal, 0, len(xx), f, 5)
                    nets.append(L["net"]); br.append(L["breaches"])
                n = np.array(nets); res[f"buffer {buf:.2f}" + (" +open" if cop else "")] = {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P_profit": round(float((n > 0).mean()), 3), "funded breaches": round(float(np.mean(br)), 3)}
        k = f"{win} " + ("backtest" if lvl is None else f"Sharpe {lvl}"); out[k] = res; print(k, flush=True)
        for a, v in res.items():
            print("  ", a, v, flush=True)
(ROOT / "results/gen415.json").write_text(json.dumps(out, indent=1))
