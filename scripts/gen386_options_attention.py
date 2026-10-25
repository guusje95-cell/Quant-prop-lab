"""Gen386 (config/gen386_protocol.json). Writes results/gen386.json and results/gen386_basket_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen384_positioning.py").read().split("b380 = pd.read_parquet")[0]
g = {"__file__": str(ROOT / "scripts/gen384_positioning.py")}; exec(compile(src, "g384", "exec"), g)
POOL, hourly_pnl, from_daily, daily, z, idx, dd, shp, per, unit, END, CS, base, K1, days = (g[k] for k in (
    "POOL", "hourly_pnl", "from_daily", "daily", "z", "idx", "dd", "shp", "per", "unit", "END", "CS", "base", "K1", "days"))
ND = ROOT / "research_data/newdata"
def att(f, lag=2):                                       # as Gen381
    s = pd.read_parquet(ROOT / f"research_data/attention/{f}")["interest"].astype(float); s.index = pd.DatetimeIndex(s.index)
    s = s.reindex(days).ffill(); m = np.log(s.rolling(7).mean() / s.rolling(30).mean()); return z(m, 180).shift(lag)
NEW = {}; O = {c: pd.read_parquet(ROOT / f"research_data/deribit_options/{c}_options_daily.parquet") for c in ("BTC", "ETH")}
def opt(c, f):
    x = O[c].copy(); x["day"] = pd.to_datetime(x["day"]); return daily(f(x))
pc = lambda x: x[x.type == "P"].groupby("day")["amount"].sum() / x[x.type == "C"].groupby("day")["amount"].sum()
def blk(x):
    b = x[x.block > 0]; s = lambda q: b[q].groupby("day")["block"].sum()
    num = s((b.type == "C") & (b.side == "buy")).sub(s((b.type == "P") & (b.side == "buy")), fill_value=0.0); return (num / b.groupby("day")["block"].sum()).fillna(0.0)
def inv(x):
    a = x[x.mny == "0.95-1.05"]; iv = lambda t: a[a.ten == t].groupby("day")["iv_sum"].sum() / a[a.ten == t].groupby("day")["n"].sum()
    return iv("<8d") / iv("8-45d")
def froth(x):
    b = x[x.side == "buy"]; return b[(b.type == "C") & (b.mny == ">1.15")].groupby("day")["amount"].sum() / b.groupby("day")["amount"].sum()
pcw = lambda f, sgn: pd.DataFrame({c: sgn * 0.125 * f(c).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
NEW["O1 put/call volume contrarian"] = pcw(lambda c: z(opt(c, pc), 90), 1)
NEW["O2 block call-minus-put buying"] = pcw(lambda c: z(opt(c, blk).rolling(7).sum(), 90), 1)
NEW["O3 short-dated IV inversion"] = pcw(lambda c: z(opt(c, inv), 90), 1)
NEW["O4 OTM call froth"] = pcw(lambda c: z(opt(c, froth).rolling(7).mean(), 90), -1)
both = lambda s, k: pd.DataFrame({"BTC": k * s.clip(-2, 2) / 2, "ETH": k * s.clip(-2, 2) / 2})
NEW["G1 crypto attention momentum"] = both(att("google_crypto_1d.parquet"), 0.125)
NEW["G2 dogecoin froth"] = both(att("google_dogecoin_1d.parquet"), -0.125)
mr = daily(pd.read_parquet(ND / "bc_miners-revenue.parquet")["miners-revenue"])
NEW["R1 miner revenue momentum"] = pd.DataFrame({"BTC": 0.25 * z(np.log(mr).diff(30), 365).clip(-2, 2) / 2})
for k, w in NEW.items():
    POOL[k] = hourly_pnl(from_daily(w.reindex(days), 0), 1.0).reindex(idx).fillna(0.0)
ref_book = pd.read_parquet(ROOT / "results/gen385_book_hourly.parquet")["book"]; REF = (shp(ref_book), per(ref_book))
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
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
out = {"reference v9.2 candidate": [REF[0], REF[1]], "new signals": {k2: rows[k2] for k2 in NEW}, "kept": kept, "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh),
       "v9.2 structure + new basket": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen386_basket_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen386_book_hourly.parquet")
(ROOT / "results/gen386.json").write_text(json.dumps(out, indent=1))
for k2, v in out["new signals"].items(): print(k2, v)
print({k2: v for k2, v in out.items() if k2 != "new signals"})
