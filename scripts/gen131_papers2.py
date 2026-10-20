"""Gen131 (config/gen131_protocol.json) O1/O2: crypto order-flow cross-section, CME bitcoin retail positioning. F1 runs separately
(needs FOMC dates). Writes results/gen131_crypto.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen80_112_breadth.py")}
exec(open(ROOT / "scripts/gen80_112_breadth.py").read().split("ref = book(")[0], g)
B, PACK, XS, EXTRA, perp_daily, book, rows, DAYS = (g[k] for k in ("B", "PACK", "XS", "EXTRA", "perp_daily", "book", "rows", "DAYS"))


def flow_daily(c):
    if c in PACK:
        k = B.k5(c); qv = k.quote_volume.resample("1D").sum(); tb = (k.taker_buy_volume * k.close).resample("1D").sum()
    else:
        k = pd.read_parquet(EXTRA / f"{c}USDT_1h.parquet"); k.index = pd.DatetimeIndex(k.index)
        qv = k.quote_volume.astype(float).resample("1D").sum(); tb = k.taker_buy_quote_volume.astype(float).resample("1D").sum()
    return pd.DataFrame({"qv": qv, "tb": tb}).loc[:"2026-09-30"]


ALL = PACK + XS; FL = {c: flow_daily(c) for c in ALL}
ratio = pd.DataFrame({c: (2 * f.tb.rolling(7).sum() - f.qv.rolling(7).sum()) / f.qv.rolling(7).sum() for c, f in FL.items()}).reindex(DAYS)
listed = pd.DataFrame({c: f.qv.gt(0).cumsum() for c, f in FL.items()}).reindex(DAYS).ffill().fillna(0) >= 60
W = pd.DataFrame(np.nan, index=DAYS, columns=ALL)
for d in DAYS[DAYS.weekday == 6]:                                        # decided at the Sunday close, held Monday..Sunday
    s = ratio.loc[d].where(listed.loc[d]).dropna()
    if len(s) < 10:
        continue
    n = max(1, len(s) // 5); w = pd.Series(0.0, index=ALL)
    w[s.nlargest(n).index] = 1.0 / n; w[s.nsmallest(n).index] = -1.0 / n; W.loc[d] = w
W = W.ffill().fillna(0.0)
book("O1 weekly order-flow cross-section (60 coins)", perp_daily(W, ALL), add=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen131_crypto.csv", index=False)

# O2 CME bitcoin retail (non-reportable) positioning, contrarian
g2 = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g2)
g3 = {"__file__": str(ROOT / "scripts/gen119_cot.py")}
src = open(ROOT / "scripts/gen119_cot.py").read(); exec(src[:src.index("def weekly_to_daily")].split("src = open")[0] + src[src.index("M2 = "):src.index("def weekly_to_daily")], g3)
b = g3["load"]("cot_tff.parquet", {"BTC": "133741"}, ["NonRept_Positions_Long_All", "NonRept_Positions_Short_All"])["BTC"]
ns = (b.NonRept_Positions_Short_All - b.NonRept_Positions_Long_All) / b.Open_Interest_All; dns = ns.diff()
z = (dns - dns.rolling(52, min_periods=40).mean()) / dns.rolling(52, min_periods=40).std()
s = pd.Series(np.where(z > 1, 0.5, np.where(z < -1, -0.5, 0.0)), index=z.index); s.index = s.index + pd.Timedelta(days=5)
days = g2["days"]; w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
w["BTC"] = s.reindex(s.index.union(days)).ffill().reindex(days).fillna(0.0)
print("O2 active days:", int((w.BTC != 0).sum()), flush=True)
g2["evaluate"]("O2 CME bitcoin retail positioning (contrarian)", w)
pd.DataFrame(g2["rows"]).to_csv(ROOT / "results/gen131_o2.csv", index=False)
