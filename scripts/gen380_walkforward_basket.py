"""Gen380 (config/gen380_protocol.json): diversifier basket selected on 2022-24 only. Writes results/gen380.json.
Needs results/k1_sleeves.parquet (k1_sleeves_save.py) and results/gen342_sleeves.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen379b_part2.py").read().split("P0 = members()")[0]
g = {"__file__": str(ROOT / "scripts/gen379b_part2.py")}; exec(compile(src, "g379b2", "exec"), g)
members, hourly_pnl, from_daily, daily, z, idx, dd, shp, END, ND, B, CS = (g[k] for k in ("members", "hourly_pnl", "from_daily", "daily", "z", "idx", "dd", "shp", "END", "ND", "B", "CS"))
days = g["days"]
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
base = pd.read_parquet(ROOT / "results/k1_sleeves.parquet"); K1 = unit(CS.portfolio_v5(base)[0]); REF = (shp(K1), per(K1))
POOL = dict(members())
pv = sum(B.k5(c).quote_volume.resample("1D").sum() for c in ("BTC", "ETH")).reindex(days)
n1 = z(np.log(daily(pd.read_parquet(ND / "defillama_dex_volume.parquet")["volume_usd"])) - np.log(pv.shift(1)), 180)
POOL["N1 speculation froth"] = hourly_pnl(from_daily(pd.DataFrame({"BTC": -0.125 * n1.clip(-2, 2) / 2, "ETH": -0.125 * n1.clip(-2, 2) / 2}), 0), 1.0)
fa, fb = {}, {}
for c in ("BTC", "ETH"):
    by = pd.read_parquet(ROOT / f"research_data/bybit/funding/{c}USDT.parquet")["funding_rate"]; by.index = pd.DatetimeIndex(by.index)
    dv = (daily(by, "sum") - daily(B.funding(c), "sum")).rolling(7).mean(); fa[c] = -0.125 * z(dv, 90).clip(-2, 2) / 2
    px = B.k5(c).close.resample("1D").last()
    o = pd.read_parquet(ND / f"bybit_{c}_oi_1d.parquet")["openInterest"]; o.index = pd.DatetimeIndex(o.index).floor("D")
    oby = (o * px.reindex(o.index)).reindex(days); obn = B.metrics(c)["sum_open_interest_value"].resample("1D").last().reindex(days)
    fb[c] = -0.125 * z((oby / (oby + obn)).shift(1).diff(7), 90).clip(-2, 2) / 2
POOL["Gen378 A funding divergence"] = hourly_pnl(from_daily(pd.DataFrame(fa), 0), 1.0)
POOL["Gen378 B OI share divergence"] = hourly_pnl(from_daily(pd.DataFrame(fb), 0), 1.0)
mp = daily(pd.read_parquet(ND / "bc_mempool-size.parquet")["mempool-size"], "mean")
POOL["Gen378 C mempool congestion"] = hourly_pnl(from_daily(pd.DataFrame({"BTC": -0.25 * z(mp, 90).clip(-2, 2) / 2}), 0), 1.0)
G = pd.read_parquet(ROOT / "results/gen342_sleeves.parquet")
for c in ("A attention momentum", "kimchi BTC/ETH v8.4", "C late-UTC BTC/ETH seasonality", "Gen249 A USDT premium", "Gen249 B ETH-BTC premium spread",
          "Gen202 VM", "Gen202 BCX", "Gen202 R1X", "Gen187 oil timing", "Gen171 CC1 FOMC weeks", "Gen171 CC2 calendar union",
          "Gen120 D1 put-skew contrarian", "Gen120 D2 call-minus-put flow", "A Bitfinex whale long change", "B Bitfinex long/short ratio"):
    POOL[c] = G[c].reindex(idx).fillna(0.0)
K1d = dd(K1).loc["2022":"2024"]; rows = {}
for nm, h in POOL.items():
    h = h.reindex(idx).fillna(0.0); POOL[nm] = h
    rows[nm] = {"2022": shp(h, "2022", "2022"), "2023-24": shp(h, "2023", "2024"), "2022-24": shp(h, "2022", "2024"),
                "corr K1 2022-24": round(float(pd.concat([dd(h).loc["2022":"2024"], K1d], axis=1).corr().iloc[0, 1]), 3), "2025-26 (record)": shp(h, "2025", END)}
elig = [k for k, v in rows.items() if v["2022"] > 0 and v["2023-24"] > 0 and abs(v["corr K1 2022-24"]) < 0.3]
kept = []
for k in sorted(elig, key=lambda k: -rows[k]["2022-24"]):
    if all(abs(float(pd.concat([dd(POOL[k]), dd(POOL[x])], axis=1).loc["2022":"2024"].corr().iloc[0, 1])) < 0.7 for x in kept):
        kept.append(k)
Dk = pd.DataFrame({k: dd(POOL[k]) for k in kept}).loc["2022":"2024"]; sdv = Dk.std()
bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(CS.portfolio_v5(base.assign(**{"diversifier basket": bh}))[0]); B1, k = shp(b), per(b)
out = {"reference K1": [REF[0], REF[1]], "pool": rows, "eligible (2022-24)": elig, "kept": kept,
       "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh), "basket corr K1 (2022-26)": round(float(pd.concat([dd(bh), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
       "K1 + basket": [B1, k],
       "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)) and k[2] >= REF[1][2])}
bh.to_frame("basket").to_parquet(ROOT / "results/gen380_basket_hourly.parquet")
(ROOT / "results/gen380.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "pool"}, indent=1))
for k, v in rows.items(): print(k, v)
