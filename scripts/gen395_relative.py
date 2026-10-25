"""Gen395 (config/gen395_protocol.json). Writes results/gen395.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, dd, shp, per, unit, END, CS, daily, z, days, pnl_daily, idx, K1 = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "CS", "daily", "z", "days", "pnl_daily", "idx", "K1"))
B = g["B"]; C3 = ("BTC", "ETH", "SOL")
V = pd.read_parquet(ROOT / "results/v93_sleeves.parquet"); v93 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v93), per(v93))
MET = {"R1 top-trader accounts": lambda c: daily(B.metrics(c)["count_toptrader_long_short_ratio"], "mean"),
       "R2 retail accounts": lambda c: daily(B.metrics(c)["count_long_short_ratio"], "mean"),
       "R3 leverage build-up": lambda c: np.log(daily(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))).diff(7),
       "R4 funding": lambda c: daily(B.funding(c), "sum").rolling(7).mean(),
       "R5 premium": lambda c: daily(B.premium(c)["close"], "mean").rolling(7).mean()}
res = {}
for nm, f in MET.items():
    Z = pd.DataFrame({c: z(f(c), 90) for c in C3}); Zd = Z.sub(Z.mean(axis=1), axis=0)
    w = (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
    POOL[nm] = pnl_daily(w).reindex(idx).fillna(0.0)
    res[nm] = {"2022 / 2023-24 / 2025-26": per(POOL[nm]), "corr K1": round(float(pd.concat([dd(POOL[nm]), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)}
    print(nm, res[nm], flush=True)
D = pd.DataFrame({k: dd(v) for k, v in POOL.items()}).loc["2022":END].fillna(0.0); D24 = D.loc[:"2024"]; K1d = dd(K1).loc["2022":"2024"]
cand = [k for k in D if abs(float(pd.concat([D24[k], K1d], axis=1).corr().iloc[0, 1])) < 0.3 and D24[k].std() > 0]
def bsr(keys):
    x = (D24[keys] / D24[keys].std()).sum(axis=1); return float(x.mean() / x.std() * np.sqrt(365))
kept, cur, steps = [], -9.0, []
while True:
    best = max(((k, bsr(kept + [k])) for k in cand if k not in kept), key=lambda t: t[1], default=(None, -9))
    if best[0] is None or best[1] < cur + 0.05:
        break
    kept.append(best[0]); cur = best[1]; steps.append([best[0], round(cur, 3)])
sdv = D24[kept].std(); bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bh.reindex(V.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
out = {"reference v9.3": [REF[0], REF[1]], "new": res, "steps": steps, "basket": per(bh), "book": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen395_basket_hourly.parquet")
(ROOT / "results/gen395.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
