"""Gen90 follow-up: crypto-firm prop results for candidate v6 (v5 + deleveraging bounce) vs v5, Gen79 adopted settings.
Writes results/gen90_v6_prop.csv and results/gen90_v6_stats.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
H5 = CS.v5_sleeves()
books = {"v6 (v5 + deleveraging bounce)": CS.portfolio_v5(pd.concat([H5, CS.delev_bounce().rename("delev bounce")], axis=1).fillna(0.0))[0],
         "v5": CS.portfolio_v5(H5)[0]}
rows, P = [], []
for n, h in books.items():
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; x = d * 0.15 / (d.std() * np.sqrt(365))
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    rows.append({"book": n, "Sharpe": x.mean() / x.std() * np.sqrt(365), "CAGR@15%vol": eq.iloc[-1] ** (365 / len(x)) - 1, "MaxDD": (eq / eq.cummax() - 1).min(),
                 "pos months": (m > 0).mean(), "worst month": m.min(), **{str(k.year): v for k, v in y.items()}})
    hh = h.loc["2022-01-01":"2026-09-30 23:00"]; hh = hh * 0.15 / (d.std() * np.sqrt(365))
    for key, (sc, sf, st) in (("HyroTrader One-Step $100k", (1.25, 1.0, 0.6)), ("HyroTrader Two-Step $100k", (1.5, 1.0, 0.5))):
        if key not in PF.PRESETS:
            key = [k for k in PF.PRESETS if k.startswith(key.split(" $")[0])][0]
        f = PF.PRESETS[key]; hc = to_daily_stop(hh * sc, st * f.daily_loss); hf = to_daily_stop(hh * sf, st * f.daily_loss)
        a = PF.attempts(hc, f, 1.0); pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
        P.append({"book": n, "firm": key, "setting": f"{sc}/{sf}/{st}", "pass": a["P_pass"], "mean_net": pb["net_mean"], "p10": pb["net_p10"], "P_profit": pb["P_profit"]})
        print(P[-1], flush=True)
S = pd.DataFrame(rows); print(S.round(3).to_string(), flush=True); S.to_csv(ROOT / "results/gen90_v6_stats.csv", index=False)
pd.DataFrame(P).to_csv(ROOT / "results/gen90_v6_prop.csv", index=False)
