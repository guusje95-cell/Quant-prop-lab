"""Gen230 (config/gen230_protocol.json): prop settings for v7 / bf, chosen on 2022-24, evaluated on 2025-26. Writes results/gen230.json."""
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
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(open(ROOT / "scripts/gen171_crypto_calendar.py").read().split("\ndays = pd.date_range")[0], g)
k = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], k)
bf = k["CS"].portfolio_v5(pd.concat([k["HB0"], (k["p6"]() + k["r1"](1e-4)).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
BOOKS = {"v7": (g["v7"], PF.PRESETS["HyroTrader Two-Step $100k"], (1.5, 1.0, 0.5)),
         "bf": (bf, replace(PF.PRESETS["BrightFunded Two-Step Classic $100k"], fee=591.0), (1.5, 1.0, 0.6))}


def run(h, f, sc, sf, st, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * sc, st * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * sf, st * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "P_funded": round(pb["P_funded"], 3)}


out = {}
for n, (hb, f, cur) in BOOKS.items():
    h = hb.loc["2022-01-01":"2026-09-30 23:00"]; dd = h.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    h = h * 0.15 / (dd.std() * np.sqrt(365))
    rows = []
    for sc, sf, st in itertools.product((1.0, 1.5, 2.0), (0.75, 1.0, 1.5), (0.5, 0.7)):
        r = run(h, f, sc, sf, st, "2022-01-01", "2024-12-31 23:00"); rows.append({"sc": sc, "sf": sf, "st": st, **r}); print(n, rows[-1], flush=True)
    T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.90]
    ch = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
    chosen = (float(ch.sc), float(ch.sf), float(ch.st))
    ev_ch = run(h, f, *chosen, "2025-01-01", "2026-09-30 23:00"); ev_cur = run(h, f, *cur, "2025-01-01", "2026-09-30 23:00")
    out[n] = {"chosen (2022-24)": chosen, "current": cur, "2025-26 chosen": ev_ch, "2025-26 current": ev_cur,
              "adopt": bool(chosen != cur and ev_ch["net"] > ev_cur["net"] and ev_ch["P_profit"] >= ev_cur["P_profit"] - 0.02)}
    T.to_csv(ROOT / f"results/gen230_{n}_grid.csv", index=False)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen230.json", "w"), indent=1)
