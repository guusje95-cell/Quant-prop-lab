"""Gen416 (descriptive decision tool): crypto-perp prop firms for v9.5 at planning Sharpe 1.41.
Per firm, the challenge / funded risk is chosen on the 2022-24 bootstrap (highest mean net among cells with P(profit) within
0.02 of the best cell), then reported on 2025-26. Daily stop 0.5 x the firm's daily limit. Writes results/gen416.json."""
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
x0 = unit(shift_to(b, 1.41)); P = PF.PRESETS
FIRMS = {k: P[k] for k in ("HyroTrader Two-Step $200k", "HyroTrader Two-Step $100k", "HyroTrader One-Step $100k", "HyroTrader Zero-Step $100k",
                           "Crypto Fund Trader 2-Phase $100k", "Crypto Fund Trader 2-Phase $100k + weekly payouts + 90% split", "Crypto Fund Trader 1-Phase $100k",
                           "Breakout One-Step Classic $100k", "Breakout Two-Step $100k", "SizeProp One-Step $100k", "SizeProp Degen $100k")}
FIRMS["MFP Signature $100k (as plan_v95)"] = replace(P["HyroTrader Two-Step $200k"], name="MFP", account=100000, fee=696.0, targets=(0.10,), daily_loss=0.03, max_loss=0.06, max_type="static", min_days=0, payout_min=0)
GRID = [(c, f) for c in (0.75, 1.0, 1.5, 2.0) for f in (0.75, 1.0, 1.5)]
def run(f, A, Z, sc, sf):
    x = x0.loc[A:Z]; ch, fd = to_daily_stop(x * sc, 0.5 * f.daily_loss), to_daily_stop(x * sf, 0.5 * f.daily_loss); idx = ch.index.intersection(fd.index)
    paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 300, 20, 11); per_day = len(idx) / max(1, cal0[-1])
    rc, loc, hic = PF._arrays(ch.reindex(idx).fillna(0.0), 1.0); rf, lof, hif = PF._arrays(fd.reindex(idx).fillna(0.0), 1.0); n = []
    for _, xx in paths:
        cal = (np.arange(len(xx)) / per_day).astype(int); n.append(PF._ledger(rc[xx], loc[xx], hic[xx], rf[xx], lof[xx], hif[xx], cal, 0, len(xx), f, 5)["net"])
    n = np.array(n); return {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P_profit": round(float((n > 0).mean()), 3)}
out = {}
for nm, f in FIRMS.items():
    tune = {(c, s): run(f, "2022-01-01", "2024-12-31 23:00", c, s) for c, s in GRID}
    best_p = max(v["P_profit"] for v in tune.values()); c, s = max((k for k, v in tune.items() if v["P_profit"] >= best_p - 0.02), key=lambda k: tune[k]["mean"])
    hold = run(f, "2025-01-01", END + " 23:00", c, s)
    out[nm] = {"fee": f.fee, "account": f.account, "chosen": f"{c}/{s}", "2022-24": tune[(c, s)], "2025-26": hold,
               "2025-26 per $100k": round(hold["mean"] * 100000 / f.account)}
    print(nm, json.dumps(out[nm]), flush=True)
(ROOT / "results/gen416.json").write_text(json.dumps(out, indent=1))
