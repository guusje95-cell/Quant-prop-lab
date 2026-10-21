"""Gen273 (config/gen273_protocol.json): CME asset-manager positioning; stablecoin dominance (vs v8.1). Writes results/gen273.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END; days = pd.date_range("2020-01-01", END)
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; save = lambda: json.dump(out, open(L.ROOT / "results/gen273.json", "w"), indent=1)
d = pd.read_parquet(L.ROOT / "research_data/more2/cot_tff.parquet")
d["asof"] = pd.to_datetime(d["As_of_Date_In_Form_YYMMDD"].astype(str).str.strip().str.zfill(6), format="%y%m%d", errors="coerce")
W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for coin, mkt in (("BTC", "BITCOIN - CHICAGO MERCANTILE EXCHANGE"), ("ETH", "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE")):
    x = d[d["Market_and_Exchange_Names"] == mkt].drop_duplicates("asof").set_index("asof").sort_index()
    am = (x["Asset_Mgr_Positions_Long_All"].astype(float) - x["Asset_Mgr_Positions_Short_All"].astype(float)) / x["Open_Interest_All"].astype(float)
    s = am - am.shift(4); z = (s - s.rolling(52, min_periods=26).mean()) / s.rolling(52, min_periods=26).std()
    z.index = z.index + pd.Timedelta(days=6)                           # Tuesday as-of -> Monday after the Friday release
    zz = z.reindex(days, method="ffill", limit=7)                      # valid for that week only
    W[coin] = np.where(zz > 1, 0.25, np.where(zz < -1, -0.25, 0.0))
out["A data to"] = str(d["asof"].max().date())
L.judge("A CME asset-manager positioning", L.perp(W), out); save()
from qpl.data import coinmetrics as CM
cap = lambda a: pd.read_csv(CM.SRC / f"{a}.csv", usecols=["time", "CapMrktCurUSD"], parse_dates=["time"]).set_index("time")["CapMrktCurUSD"]
caps = pd.DataFrame({a: cap(a) for a in ("usdt", "usdc", "btc", "eth")}); caps.index = pd.DatetimeIndex(caps.index).tz_localize(None).normalize()
caps = caps.where(caps > 0); st = caps["usdt"].fillna(0) + caps["usdc"].fillna(0)
dom = (st / (st + caps["btc"] + caps["eth"])).where(caps["btc"].notna() & caps["eth"].notna())
s = (dom / dom.shift(30) - 1).shift(2); z = (s - s.rolling(365, min_periods=180).mean()) / s.rolling(365, min_periods=180).std(); z = z.reindex(days)
w = pd.Series(np.where(z > 1, -0.25, np.where(z < -1, 0.25, 0.0)), index=days)
out["B data to"] = str(dom.dropna().index.max().date())
L.judge("B stablecoin dominance", L.perp(pd.DataFrame({"BTC": w, "ETH": w})), out); save()
