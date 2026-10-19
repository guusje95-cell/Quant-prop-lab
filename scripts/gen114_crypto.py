"""Gen114 T5-T6 (config/gen114_protocol.json): CME bitcoin basis momentum and CME weekend gap fill, into v6 and bf.
Writes results/gen114_crypto.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
g = {"__file__": str(ROOT / "scripts/gen116_spill.py")}
exec(open(ROOT / "scripts/gen116_spill.py").read().split("\nux = pd.read_parquet")[0], g)
evaluate, rows, HC, CB = g["evaluate"], g["rows"], g["HC"], g["CB"]

cme = F.front("BTC").close
bn = HC["BTC"]
# T5 basis momentum: hourly premium of CME front over Binance perp, 24h mean, z vs 30 days, read at the 20:00 UTC bar (close 21:00)
p = (cme / bn.reindex(cme.index) - 1).dropna()
p24 = p.rolling("24h", min_periods=12).mean()
z = (p24 - p24.rolling("30D", min_periods=300).mean()) / p24.rolling("30D", min_periods=300).std()
zz = z[z.index.hour <= 20]; zd = zz.groupby(zz.index.floor("D")).last()
w = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", "2026-09-30"), columns=["BTC", "ETH"])
w["BTC"] = np.where(zd.reindex(w.index) > 1, 0.5, np.where(zd.reindex(w.index) < -1, -0.5, 0.0))
evaluate("T5 CME bitcoin basis momentum", CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), HC.index)[["BTC", "ETH"]])
# T6 weekend gap: CME Friday last bar close vs Binance at the Sunday reopen; |gap| > 1% -> 0.5 toward the gap for 24h
P = pd.DataFrame(0.0, index=HC.index, columns=["BTC", "ETH"])
ci = cme.index
fri = cme[ci.weekday == 4].groupby(ci[ci.weekday == 4].normalize()).last()
sun_open = pd.Series(ci[ci.weekday == 6], index=ci[ci.weekday == 6]).groupby(ci[ci.weekday == 6].normalize()).first()
n = 0
for d, t0 in sun_open.items():
    fc = fri.get(d - pd.Timedelta(days=2))
    b = bn.get(t0 - pd.Timedelta(hours=1))                      # Binance close of the bar before the reopen = price at reopen
    if fc is None or b is None or not np.isfinite(b):
        continue
    gap = b / fc - 1
    if abs(gap) > 0.01:
        P.loc[t0:t0 + pd.Timedelta(hours=23), "BTC"] = -0.5 * np.sign(gap); n += 1
print("T6 events:", n, flush=True)
evaluate("T6 CME weekend gap fill", P)
pd.DataFrame(rows).to_csv(ROOT / "results/gen114_crypto.csv", index=False)
