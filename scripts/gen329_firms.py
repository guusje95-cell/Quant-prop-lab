"""Gen329 (config/gen329_protocol.json): v8.6 at other crypto prop firms. Same strategy, each firm's rules; risk settings chosen per firm
on 2022-24 (nested, as Gen236 / Gen318) and judged on 2025-26. Returns at the Bybit-realistic level (Gen327: 3.03) and at the
deflated planning level (Gen325: 1.78). Writes results/gen329.json."""
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
P = PF.PRESETS
HY = P["HyroTrader Two-Step $200k"]
CFT = replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1100.0, targets=(0.08, 0.04),
              note="ASSUMED fee ~2x the $100k price; targets 8% / 4% from the firm's evaluation page; 5% daily (balance 00:05 UTC); 10% static")
PROPR = replace(HY, name="Propr 2-Step 200k", fee=1000.0, targets=(0.08, 0.05), daily_loss=0.05, max_loss=0.08, max_type="trailing",
                trailing_intraday=True, min_days=0, note="rulebook: 5% daily (start-of-day balance), 8% TRAILING on equity; fee and targets ASSUMED")
MFP = replace(HY, name="MyFundedPerps Signature 200k (1-step)", fee=1000.0, targets=(0.08,), daily_loss=0.03, max_loss=0.06, max_type="static",
              min_days=0, note="reviews: 3% daily, 6% static (Signature); fee, size and target ASSUMED")
FIRMS = {"HyroTrader 2-Step $200k": HY, "Crypto Fund Trader 2-Phase $200k": CFT, "Propr 2-Step $200k": PROPR, "MyFundedPerps Signature $200k": MFP}
GRID_C, GRID_F = (0.75, 1.0, 1.25, 1.5, 2.0, 2.5), (0.75, 1.0, 1.5, 2.0)

h0 = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"].loc["2022-01-01":"2026-09-30 23:00"]


def at_sharpe(h, target):
    """constant per-hour shift so the 2022-26 daily Sharpe equals target (volatility unchanged); vol scaled to 15% on 2022-24 only."""
    d = h.groupby(h.index.floor("D")).sum(); h = h - (d.mean() - target * d.std() / np.sqrt(365)) / 24
    dd = h.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    return h * 0.15 / (dd.std() * np.sqrt(365))


def run(h, f, sc, sf, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * sc, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * sf, 0.5 * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "P_funded": round(pb["P_funded"], 3),
            "days_to_funded": pb["days_to_funded_median"], "challenges": round(pb["bought"], 2)}


out = {}
for lvl, target in (("realistic (Bybit costs, Sharpe 3.03)", 3.03), ("planning (deflated, Sharpe 1.78)", 1.78)):
    h = at_sharpe(h0, target); out[lvl] = {}
    for fn, f in FIRMS.items():
        rows = [{"sc": sc, "sf": sf, **run(h, f, sc, sf, "2022-01-01", "2024-12-31 23:00")} for sc, sf in itertools.product(GRID_C, GRID_F)]
        T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; r = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
        res = {"chosen on 2022-24 (challenge risk, funded risk)": [float(r.sc), float(r.sf)],
               "2025-26 at the chosen risk": run(h, f, float(r.sc), float(r.sf), "2025-01-01", "2026-09-30 23:00"),
               "2025-26 at 2.0 / 1.5": run(h, f, 2.0, 1.5, "2025-01-01", "2026-09-30 23:00"), "rules": f.note or ""}
        out[lvl][fn] = res; print(lvl, fn, res, flush=True)
json.dump(out, open(ROOT / "results/gen329.json", "w"), indent=1, default=float)
