"""Gen372 (config/gen372_protocol.json): the Gen321 fallback book and a point-in-time version of its 20-coin carry. Writes results/gen372.json.
    cd scripts && python gen372_honest_book.py <v86 dump parquet (paper_v5.py _dump, cutoff 2026-10-01, live 0)>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
exec(open(ROOT / "scripts/gen326_wide_carry.py").read().split("\nimport os\nREF")[0])      # Gen326 loaders and sleeve(K)
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
H0 = pd.read_parquet(DUMP).drop(columns="port").loc[:"2026-09-30 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
shp = lambda h, a, z: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
HY = PF.PRESETS["HyroTrader Two-Step $200k"]


def prop(h, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * HY.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


p20, n20 = sleeve(20); p20 = p20.reindex(H0.index).fillna(0.0)
F0 = H0.drop(columns="premium carry 60")
BOOKS = {"v86": H0, "F0 fallback": F0, "F1 point-in-time 20-coin carry": F0.assign(**{"premium carry": p20}), "F2 no carry": F0.drop(columns="premium carry")}
out = {"pit top-20 mean universe size": round(n20, 1),
       "carry sleeve 2022 / 2023-24 / 2025-26 (survivor 20 vs pit 20)": {"survivor": [shp(H0["premium carry"], a, z) for a, z in (("2022", "2022"), ("2023", "2024"), ("2025", END))],
                                                                         "pit": [shp(p20, a, z) for a, z in (("2022", "2022"), ("2023", "2024"), ("2025", END))]}}
for k, Hk in BOOKS.items():
    b = unit(CS.portfolio_v5(Hk)[0])
    out[k] = {"Sharpe 2022-26 [2022, 2023-24, 2025-26]": [shp(b, "2022", END), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", END)]],
              "HyroTrader 2022-24": prop(b, "2022-01-01", "2024-12-31 23:00"), "HyroTrader 2025-26": prop(b, "2025-01-01", END + " 23:00")}
    print(k, out[k], flush=True)
s = lambda k: out[k]["Sharpe 2022-26 [2022, 2023-24, 2025-26]"]
if s("F0 fallback")[0] - s("F1 point-in-time 20-coin carry")[0] <= 0.10:
    out["chosen"] = "F0 fallback"
else:
    f1, f2 = s("F1 point-in-time 20-coin carry"), s("F2 no carry")
    out["chosen"] = "F2 no carry" if (f2[0] >= f1[0] + 0.05 and all(f2[1][i] >= f1[1][i] for i in range(3))) else "F1 point-in-time 20-coin carry"
out["honest backtest Sharpe (point-in-time carry)"] = s("F1 point-in-time 20-coin carry")[0] if out["chosen"] != "F2 no carry" else s("F2 no carry")[0]
out["planning Sharpe (x 1.78 / 3.11)"] = round(out["honest backtest Sharpe (point-in-time carry)"] * 1.78 / 3.11, 2)
(ROOT / "results/gen372.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
