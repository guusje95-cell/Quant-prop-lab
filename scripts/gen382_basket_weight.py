"""Gen382 (config/gen382_protocol.json). Writes results/gen382.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen380_walkforward_basket.py").read().split("K1d = dd(K1)")[0]
g = {"__file__": str(ROOT / "scripts/gen380_walkforward_basket.py")}; exec(compile(src, "g380", "exec"), g)
POOL, dd, shp, per, unit, END, CS, base = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "CS", "base"))
kept = json.loads((ROOT / "results/gen380.json").read_text())["kept"]
bh = pd.read_parquet(ROOT / "results/gen380_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
v91 = unit(CS.portfolio_v5(base.assign(**{"diversifier basket": bh}))[0]); REF = (shp(v91), per(v91))
def weighted(Hk, col, m):
    ph0, W, mult = CS.portfolio_v5(Hk); W2 = W.copy(); W2[col] *= m
    Wh = W2.reindex(Hk.index.floor("D")).set_axis(Hk.index); raw = (Hk * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    tgt = (0.15 / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    return unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
T = {"A members as sleeves": unit(CS.portfolio_v5(base.assign(**{k: POOL[k].reindex(base.index).fillna(0.0) for k in kept}))[0]),
     "B basket x2": weighted(base.assign(**{"diversifier basket": bh}), "diversifier basket", 2.0),
     "C basket x3": weighted(base.assign(**{"diversifier basket": bh}), "diversifier basket", 3.0)}
out = {"reference v9.1": [REF[0], REF[1]], "check: x1 reproduces v9.1": shp(weighted(base.assign(**{"diversifier basket": bh}), "diversifier basket", 1.0)), "trials": {}}
for k, b in T.items():
    out["trials"][k] = {"2022-24": shp(b, "2022", "2024"), "2022-26 [periods]": [shp(b), per(b)], "worst day at risk 2": round(float(2 * dd(b).loc["2022":].min()), 4)}
ch = max(T, key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["2022-26 [periods]"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
from qpl.lab import propfirms as PF
s9 = open(ROOT / "scripts/gen90_books.py").read(); exec(s9[s9.index("def to_daily_stop"):s9.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
def prop(h, a, z_):
    x = h.loc[a:z_]; pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * HY.daily_loss), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
out["chosen prop (HyroTrader 2022-24 / 2025-26)"] = [prop(T[ch], "2022-01-01", "2024-12-31 23:00"), prop(T[ch], "2025-01-01", END + " 23:00")]
T[ch].to_frame("book").to_parquet(ROOT / "results/gen382_book_hourly.parquet")
(ROOT / "results/gen382.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
