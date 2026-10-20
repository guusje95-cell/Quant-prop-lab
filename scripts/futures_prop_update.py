"""Prop simulation of the futures book, Gen143 (0.674) vs Gen166 (1.102), on the UNSEEN window 2023-01..2026-09 only
(block bootstrap of that window, 2-year horizon, 500 paths, re-buy budget 5). Firm terms ASSUMED as in the overview. Writes results/futures_prop_update.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
FIRM = PF.Firm("Swing futures firm 50k (MFFU/Tradeify-like, ASSUMED)", 50_000, 150, (0.06,), 0.0, "initial", True, 0.04, "trailing_lock", False,
               2, 0, 0.90, 14, 0.0, False, 0.0, "ASSUMED terms, verify on the firm's site.", payout_min=250)
rows = []
for name, f in (("Gen143 book (old)", "gen143_book"), ("Gen166 book (current)", "gen166_book")):
    x = pd.read_parquet(ROOT / f"results/{f}.parquet")["book"].loc["2023-01-01":"2026-09-30"]
    x = x * 0.15 / (x.std() * np.sqrt(252))
    d = pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})
    for sc in (0.33, 0.5, 0.75):
        a = PF.attempts(d, FIRM, sc); pb = PF.pipeline(d, FIRM, 5, 1, sc, sc, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
        rows.append({"book": name, "risk (x15% vol)": sc, "Sharpe 2023-26": round(float(x.mean() / x.std() * np.sqrt(252)), 2), "P(pass per attempt)": round(a["P_pass"], 2),
                     "net 2y mean": round(pb["net_mean"]), "net 2y p10": round(pb["net_p10"]), "P(profit)": round(pb["P_profit"], 2), "net per month": round(pb["net_per_month"]),
                     "days to 1st payout (median)": pb["days_to_first_payout_median"]})
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/futures_prop_update.csv", index=False)
