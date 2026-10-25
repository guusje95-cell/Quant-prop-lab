"""Gen394 (config/gen394_protocol.json). Writes results/gen394.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, dd, shp, per, unit, END, CS, daily, z, days, pnl_daily, idx = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "CS", "daily", "z", "days", "pnl_daily", "idx"))
B = g["B"]; ND = ROOT / "research_data/newdata"
V = pd.read_parquet(ROOT / "results/v93_sleeves.parquet"); v93 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v93), per(v93))
kept = [s[0] for s in json.loads((ROOT / "results/gen391.json").read_text())["steps (member, basket 2022-24 Sharpe)"]]
W = {"S6 top-trader crowding": pd.DataFrame({c: -0.125 * z(daily(B.metrics(c)["count_toptrader_long_short_ratio"], "mean"), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")}),
     "M5 leverage build-up": pd.DataFrame({c: -0.125 * z(np.log(daily(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))).diff(7), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})}
st = daily(pd.read_parquet(ND / "defillama_stablecoins.parquet")["stablecoin_usd"]); n2 = z(np.log(st).diff(30), 365)
W["stablecoin impulse"] = pd.DataFrame({"BTC": 0.125 * n2.clip(-2, 2) / 2, "ETH": 0.125 * n2.clip(-2, 2) / 2})
n3 = z(daily(pd.read_parquet(ND / "bc_transaction-fees-usd.parquet")["transaction-fees-usd"]), 90)
W["fee pressure"] = pd.DataFrame({"BTC": -0.25 * n3.clip(-2, 2) / 2})
chk = {k: round(float(np.corrcoef(dd(pnl_daily(w).reindex(idx).fillna(0.0)).loc["2022":], dd(POOL[k]).loc["2022":])[0, 1]), 3) for k, w in W.items()}
def basket(k):
    P = dict(POOL)
    for nm, w in W.items():
        P[nm] = pnl_daily(w.reindex(days).fillna(0.0).rolling(k, min_periods=1).mean()).reindex(idx).fillna(0.0)
    sdv = pd.DataFrame({m: dd(P[m]) for m in kept}).loc["2022":"2024"].std(); bh = sum(P[m] / sdv[m] for m in kept)
    return bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
out = {"reference v9.3": [REF[0], REF[1]], "check: rebuilt members vs pool (corr)": chk, "trials": {}}
for nm, k in (("A k = 3", 3), ("B k = 7", 7)):
    bh = basket(k); b = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bh.reindex(V.index).fillna(0.0)}))[0])
    out["trials"][nm] = {"basket": per(bh), "2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)]}
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
(ROOT / "results/gen394.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
