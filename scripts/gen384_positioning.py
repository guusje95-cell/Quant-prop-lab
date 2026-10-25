"""Gen384 (config/gen384_protocol.json). Writes results/gen384.json and results/gen384_basket_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen381_more_signals.py").read().split("# v9.1 reference")[0]
g = {"__file__": str(ROOT / "scripts/gen381_more_signals.py")}; exec(compile(src, "g381", "exec"), g)
POOL, hourly_pnl, from_daily, daily, z, idx, dd, shp, per, unit, END, B, CS, base, K1, days = (g[k] for k in (
    "POOL", "hourly_pnl", "from_daily", "daily", "z", "idx", "dd", "shp", "per", "unit", "END", "B", "CS", "base", "K1", "days"))
def rdp(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()
NEW = {}
per_coin = lambda f, sgn: pd.DataFrame({c: sgn * 0.125 * f(c).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
NEW["M1 retail crowding"] = per_coin(lambda c: z(daily(B.metrics(c)["count_long_short_ratio"], "mean"), 90), -1)
NEW["M2 top-trader position crowding"] = per_coin(lambda c: z(daily(B.metrics(c)["sum_toptrader_long_short_ratio"], "mean"), 90), -1)
NEW["M3 premium discount"] = per_coin(lambda c: z(daily(B.premium(c)["close"], "mean").rolling(7).mean(), 90), -1)
NEW["M4 funding contrarian"] = per_coin(lambda c: z(daily(B.funding(c), "sum").rolling(7).mean(), 90), -1)
NEW["M5 leverage build-up"] = per_coin(lambda c: z(np.log(daily(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))).diff(7), 90), -1)
def spotlead(c):
    sp = rdp(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet"); qcol = "quote_volume" if "quote_volume" in sp else sp.columns[-1]
    s = daily(sp[qcol].astype(float), "sum"); p = daily(B.k5(c).quote_volume, "sum"); return z(np.log(s / p).rolling(7).mean(), 90)
NEW["M6 spot-led demand"] = per_coin(spotlead, 1)
for k, w in NEW.items():
    POOL[k] = hourly_pnl(from_daily(w.reindex(days), 0), 1.0).reindex(idx).fillna(0.0)
b380 = pd.read_parquet(ROOT / "results/gen380_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
v91 = unit(CS.portfolio_v5(base.assign(**{"diversifier basket": b380}))[0]); REF = (shp(v91), per(v91))
K1d = dd(K1).loc["2022":"2024"]; rows = {}
for nm, h in POOL.items():
    rows[nm] = {"2022": shp(h, "2022", "2022"), "2023-24": shp(h, "2023", "2024"), "2022-24": shp(h, "2022", "2024"),
                "corr K1 2022-24": round(float(pd.concat([dd(h).loc["2022":"2024"], K1d], axis=1).corr().iloc[0, 1]), 3), "2025-26 (record)": shp(h, "2025", END)}
elig = [k for k, v in rows.items() if v["2022"] > 0 and v["2023-24"] > 0 and abs(v["corr K1 2022-24"]) < 0.3]
kept = []
for k in sorted(elig, key=lambda k: -rows[k]["2022-24"]):
    if all(abs(float(pd.concat([dd(POOL[k]), dd(POOL[x])], axis=1).loc["2022":"2024"].corr().iloc[0, 1])) < 0.7 for x in kept):
        kept.append(k)
sdv = pd.DataFrame({k: dd(POOL[k]) for k in kept}).loc["2022":"2024"].std()
bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(CS.portfolio_v5(base.assign(**{"diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
out = {"reference v9.1": [REF[0], REF[1]], "new signals": {k: rows[k] for k in NEW}, "kept": kept, "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh),
       "K1 + new basket": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen384_basket_hourly.parquet")
(ROOT / "results/gen384.json").write_text(json.dumps(out, indent=1))
for k2, v in out["new signals"].items(): print(k2, v)
print({k2: v for k2, v in out.items() if k2 != "new signals"})
