"""VAL-7 (2026-11-05, descriptive, 0 trials): v9.8 backtest book (results/v98_book_hourly.parquet, 2022-01..2026-09) at risk 2.0 / 1.75 / 1.5:
daily distribution (big up vs down days), the hourly-checked 2.5% daily stop (loss at the stop hour incl. 10 bp exit; firm limit 5%),
and how much N paper days can tell (standard error, chance of a negative period while the edge is intact; day bootstrap)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
b = pd.read_parquet(ROOT / "results/v98_book_hourly.parquet").book
out = {}
for R in (2.0, 1.75, 1.5):
    h = b * R; day = h.groupby(h.index.date).sum(); hits = []
    for _, g in h.groupby(h.index.date):
        c = g.cumsum().to_numpy(); k = np.flatnonzero(c <= -0.025)
        if len(k):
            hits.append(c[k[0]] - 0.001)
    hits = np.array(hits)
    out[f"risk {R}"] = {"daily mean %": round(day.mean() * 100, 3), "daily sd %": round(day.std() * 100, 2), "positive days": round(float((day > 0).mean()), 3),
                        "days >= +4.6%": int((day >= 0.046).sum()), "days <= -4.6%": int((day <= -0.046).sum()), "days": int(day.size),
                        "stop hits": len(hits), "loss at stop median %": round(float(np.median(hits)) * 100, 2), "loss at stop worst %": round(float(hits.min()) * 100, 2),
                        "stop days worse than -3.5%": int((hits <= -0.035).sum()), "firm 5% breaches": int((hits <= -0.05).sum())}
day = (b * 2).groupby(b.index.date).sum(); rng = np.random.default_rng(0)
out["what N paper days can tell (risk 2)"] = {n: {"t of the backtest mean": round(float(day.mean() / (day.std() / np.sqrt(n))), 2),
                                                  "P(negative period with the edge intact)": round(float((rng.choice(day.values, (20000, n)).sum(1) < 0).mean()), 3)} for n in (7, 56, 112, 365)}
(ROOT / "results/v99/val7_stop_overshoot.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
