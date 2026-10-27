"""Gen472c (descriptive): HyroTrader $200k accounts for v9.8 with the Gen472 Bybit filter vs v9.7 at planning levels
(one account, and a second one 180 days later; 1.5 / 1.5 / stop 0.5). Saves results/v98b_book_hourly.parquet, writes results/gen472c.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
s, _, _ = EL.pnl(idx)
b8 = unit(CS.portfolio_v5(V.drop(columns="cascade limit strict").assign(**{"listing short": s}))[0])
pd.DataFrame({"book": b8}).to_parquet(ROOT / "results/v98b_book_hourly.parquet")
b7 = unit(pd.read_parquet(ROOT / "results/v97_book_hourly.parquet")["book"])
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]; out = {}
for name, b, lvls in (("v9.7", b7, (1.44,)), ("v9.8 (Bybit filter)", b8, (1.2, 1.44, 1.64))):
    for win, (A, Z) in {"2025-26": ("2025-01-01", END + " 23:00"), "2022-24": ("2022-01-01", "2024-12-31 23:00")}.items():
        for lvl in lvls:
            x = unit(shift_to(b, lvl)).loc[A:Z]; ch = to_daily_stop(x * 1.5, 0.5 * HY.daily_loss)
            r, lo, hi = PF._arrays(ch, 1.0); cal_all = PF._days(ch.index); per_day = len(ch) / max(1, cal_all[-1])
            paths, _ = PF._paths(pd.DataFrame(index=ch.index, data={"net": 0.0}), "bootstrap", 730 + 180, 1, 400, 20, 11)
            res = {}
            for lag in (None, 180):
                tot = []
                for _, xx in paths:
                    n1 = int(730 * per_day); nets = []
                    for s0 in ((0,) if lag is None else (0, int(lag * per_day))):
                        seg = xx[s0:s0 + n1]; cal = (np.arange(len(seg)) / per_day).astype(int)
                        nets.append(PF._ledger(r[seg], lo[seg], hi[seg], r[seg], lo[seg], hi[seg], cal, 0, len(seg), HY, 5)["net"])
                    tot.append(sum(nets))
                t = np.array(tot); res["one account" if lag is None else "two accounts, second +180 d"] = {"mean": round(float(t.mean())), "p10": round(float(np.percentile(t, 10))), "P_loss": round(float((t < 0).mean()), 3)}
            out[f"{name} {win} Sharpe {lvl}"] = res; print(name, win, lvl, json.dumps(res), flush=True)
(ROOT / "results/gen472c.json").write_text(json.dumps(out, indent=1))
