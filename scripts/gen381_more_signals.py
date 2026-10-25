"""Gen381 (config/gen381_protocol.json). Writes results/gen381.json and results/gen381_basket_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen380_walkforward_basket.py").read().split("K1d = dd(K1)")[0]
g = {"__file__": str(ROOT / "scripts/gen380_walkforward_basket.py")}; exec(compile(src, "g380", "exec"), g)
POOL, hourly_pnl, from_daily, daily, z, idx, dd, shp, per, unit, END, ND, B, CS, base, K1, days = (g[k] for k in (
    "POOL", "hourly_pnl", "from_daily", "daily", "z", "idx", "dd", "shp", "per", "unit", "END", "ND", "B", "CS", "base", "K1", "days"))
M2 = ROOT / "research_data/more2"
both = lambda s, k=0.125: pd.DataFrame({"BTC": k * s.clip(-2, 2) / 2, "ETH": k * s.clip(-2, 2) / 2})
vix = pd.read_parquet(M2 / "vix_VIX.parquet")["close"]; v3 = pd.read_parquet(M2 / "vix_VIX3M.parquet")["close"]
NEW = {}
NEW["S1 VIX term structure"] = both(-z(daily(np.log(vix / v3.reindex(vix.index))), 90))
NEW["S2 VIX shock"] = both(-z(daily(np.log(vix)).diff(5), 90))
cot = pd.read_parquet(M2 / "cot_tff.parquet"); cot["d"] = pd.to_datetime(cot["As_of_Date_In_Form_YYMMDD"].astype(str).str.zfill(6), format="%y%m%d") + pd.Timedelta(days=4)
def cot_sig(name, grp):
    x = cot[cot.Market_and_Exchange_Names == name].set_index("d").sort_index()
    net = (x[f"{grp}_Positions_Long_All"] - x[f"{grp}_Positions_Short_All"]) / x["Open_Interest_All"]
    s = z(net.diff(4), 52); return s.reindex(days, method="ffill")          # usable from the Saturday after the as-of Tuesday
cn = {"BTC": "BITCOIN - CHICAGO MERCANTILE EXCHANGE", "ETH": "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE"}
NEW["S3 CME asset managers"] = pd.DataFrame({c: 0.125 * cot_sig(n, "Asset_Mgr").clip(-2, 2) / 2 for c, n in cn.items()})
NEW["S4 CME leveraged funds"] = pd.DataFrame({c: -0.125 * cot_sig(n, "Lev_Money").clip(-2, 2) / 2 for c, n in cn.items()})
fg = pd.read_parquet(ROOT / "research_data/more/fear_greed_1d.parquet")["value"].astype(float)
NEW["S5 fear and greed contrarian"] = both(-z(daily(fg), 30))
NEW["S6 top-trader crowding"] = pd.DataFrame({c: -0.125 * z(daily(B.metrics(c)["count_toptrader_long_short_ratio"], "mean"), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
NEW["S7 taker flow momentum"] = pd.DataFrame({c: 0.125 * z(daily(B.metrics(c)["sum_taker_long_short_vol_ratio"], "mean"), 30).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
NEW["S8 network activity"] = pd.DataFrame({"BTC": 0.25 * z(daily(pd.read_parquet(ND / "bc_n-transactions.parquet")["n-transactions"]), 90).clip(-2, 2) / 2})
def att(f, lag=2):
    s = pd.read_parquet(ROOT / f"research_data/attention/{f}")["interest"].astype(float); s.index = pd.DatetimeIndex(s.index)
    s = s.reindex(days).ffill(); m = np.log(s.rolling(7).mean() / s.rolling(30).mean()); return z(m, 180).shift(lag)
NEW["S9 buy-bitcoin attention"] = both(att("google_buy_bitcoin_1d.parquet"))
NEW["S10 ethereum attention"] = pd.DataFrame({"ETH": 0.25 * att("google_ethereum_1d.parquet").clip(-2, 2) / 2})
for k, w in NEW.items():
    POOL[k] = hourly_pnl(from_daily(w.reindex(days), 0), 1.0).reindex(idx).fillna(0.0)
# v9.1 reference
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
out = {"reference v9.1": [REF[0], REF[1]], "new signals": {k: rows[k] for k in NEW}, "eligible": elig, "kept": kept,
       "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh), "K1 + new basket": [B1, k],
       "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen381_basket_hourly.parquet")
(ROOT / "results/gen381.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
