"""Gen376 (config/gen376_protocol.json): four sleeves from the new free data, each added to v9.0 / K1. Writes results/gen376.json.
Deviation (stated before running): the perp-DEX volume and TVL downloads failed, so N1 uses DEX volume only.
    cd scripts && python gen376_newdata.py <v86 dump>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s373 = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s373, "g373", "exec"), g)
CS, B, H0, END = g["CS"], g["B"], g["H0"], g["END"]
ND = ROOT / "research_data/newdata"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
K1C = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
base = H0[K1C].assign(**{"C*": g["cp"]}); K1 = unit(CS.portfolio_v5(base)[0]); REF = (shp(K1), per(K1))
days = pd.date_range("2020-01-01", END[:10], freq="D")
rd = lambda n: pd.read_parquet(ND / f"{n}.parquet")
def daily(s):                                   # daily value of day d, usable at the close of d+1 (1-day publication lag)
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = s.groupby(level=0).last()
    return s.reindex(days).ffill().shift(1)
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
pv = sum(B.k5(c).quote_volume.resample("1D").sum() for c in ("BTC", "ETH")).reindex(days)
dex = daily(rd("defillama_dex_volume")["volume_usd"])
n1 = z(np.log(dex) - np.log(pv.shift(1)), 180)
st = daily(rd("defillama_stablecoins")["stablecoin_usd"]); n2 = z(np.log(st).diff(30), 365)
fees = daily(rd("bc_transaction-fees-usd")["transaction-fees-usd"]); n3 = z(fees, 90)
W = {"N1 speculation froth": pd.DataFrame({"BTC": -0.125 * n1.clip(-2, 2) / 2, "ETH": -0.125 * n1.clip(-2, 2) / 2}),
     "N2 stablecoin impulse": pd.DataFrame({"BTC": 0.125 * n2.clip(-2, 2) / 2, "ETH": 0.125 * n2.clip(-2, 2) / 2}),
     "N3 fee pressure": pd.DataFrame({"BTC": -0.25 * n3.clip(-2, 2) / 2}),
     "N4 Bybit crowding": pd.DataFrame({c: -0.25 * z(daily(rd(f"bybit_{c}_account_ratio_1d")["buyRatio"]), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})}
from qpl.lab.data import stablecoin_caps
caps = stablecoin_caps(); cf = np.sign(np.log(caps.where(caps > 0)).diff(30)).reindex(days)
out = {"reference K1": [REF[0], REF[1]], "N2 corr with the C* stablecoin filter sign": round(float(pd.concat([n2, cf], axis=1).dropna().corr().iloc[0, 1]), 3),
       "N4 history start": str(rd("bybit_BTC_account_ratio_1d").index.min().date())}
res = {}
for nm, w in W.items():
    h = CS._from_daily_weights(w.fillna(0.0), list(w.columns), 5).reindex(H0.index).fillna(0.0)
    b = unit(CS.portfolio_v5(base.assign(**{nm: h}))[0]); B1, k = shp(b), per(b); s = per(h)
    ok = bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)) and s[0] > 0 and s[1] > 0)
    if nm.startswith("N2") and abs(out["N2 corr with the C* stablecoin filter sign"]) >= 0.5:
        ok = False
    res[nm] = {"sleeve 2022 / 2023-24 / 2025-26": s, "corr with K1": round(float(pd.concat([dd(h), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
               "K1 + sleeve": [B1, k], "pass": ok}
    print(nm, res[nm], flush=True)
out["trials"] = res
(ROOT / "results/gen376.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
