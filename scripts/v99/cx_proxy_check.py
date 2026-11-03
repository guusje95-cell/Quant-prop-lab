"""F-CX live proxy check (0 trials): the CX sleeve computed on Binance BTC / ETH perps (same C* positions, CME micro costs per side,
Binance funding as the stand-in for the CME basis) vs the real CME series (F-CXb). Writes results/v99/cx_sleeve_prefix.parquet
(CME series, daily, weekend on Monday, up to 2026-09-30) and results/v99/cx_proxy_check.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
import futures_db as F
from qpl.live.futures_cx import daily, proxy_hourly

tgt = g["SLEEVES"]["S6 C* BTC/ETH legs"]
cme = daily(g["execute"](tgt, "a"))
cme.to_frame("CX").to_parquet(ROOT / "results/v99/cx_sleeve_prefix.parquet")
px = g["B"].panel("close", "1h", ["BTC", "ETH"]).loc[:"2026-09-30 23:00"]
prx = daily(proxy_hourly(tgt.reindex(px.index).fillna(0.0), px, g["CS"]._funding_hourly(["BTC", "ETH"], px.index)))
x = pd.concat([cme, prx], axis=1, keys=["cme", "proxy"]).loc["2020":].fillna(0.0); x = x[x.index.weekday < 5]
sh = lambda s: round(float(s.mean() / s.std() * np.sqrt(252)), 3)
out = {"corr daily": round(float(x.corr().iloc[0, 1]), 3), "Sharpe cme / proxy 2020-22": [sh(x.cme.loc[:"2022"]), sh(x.proxy.loc[:"2022"])],
       "Sharpe cme / proxy 2023-26": [sh(x.cme.loc["2023":]), sh(x.proxy.loc["2023":])], "mean daily diff (proxy - cme), bp": round(float((x.proxy - x.cme).mean() * 1e4), 3)}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cx_proxy_check.json").write_text(json.dumps(out, indent=1))
