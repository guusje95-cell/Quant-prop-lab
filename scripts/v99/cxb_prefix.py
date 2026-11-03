"""Writes results/v99/cxb_sleeve_prefix.parquet (F-CX5 basket on CME BTC / ETH, to 2026-09-30), checks that the live code reproduces
F-CX5 (futures + CX4 + CXB) and compares the live Binance proxy of CXB with the CME series (0 trials). Writes results/v99/cxb_proxy_check.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
import basket_live as BL
import futures_db as F
from qpl.live import futures_cx as FX

_, W = BL.basket(pd.date_range("2019-06-01", "2026-09-30 23:00", freq="h"))
bw = sum(w.reindex(columns=["BTC", "ETH"]).fillna(0.0) for w in W.values())
cme = FX.daily(g["execute"](g["d2h"](bw), "a")); cme.to_frame("CXB").to_parquet(FX.PREFIX5)
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P["CX"] = pd.read_parquet(FX.PREFIX)["CX"].add(pd.read_parquet(FX.PREFIX4)["legs"], fill_value=0.0).reindex(P.index).fillna(0.0)
P["CXB"] = cme.reindex(P.index).fillna(0.0)
out = {"futures + CX4 + CXB (live code)": [round(F.sharpe(FX.book(P)[0], *s), 3) for s in F.SPLITS]}
px = g["B"].panel("close", "1h", ["BTC", "ETH"]).loc[:"2026-09-30 23:00"]
b2 = bw.reindex(bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))).shift(1)
pos = b2.reindex(px.index.floor("D")).set_axis(px.index).fillna(0.0)
prx = FX.daily(FX.proxy_hourly(pos, px, g["CS"]._funding_hourly(["BTC", "ETH"], px.index)))
x = pd.concat([cme, prx], axis=1, keys=["cme", "proxy"]).loc["2020":].fillna(0.0); x = x[x.index.weekday < 5]
sh = lambda s: round(float(s.mean() / s.std() * np.sqrt(252)), 3)
out.update({"proxy corr daily": round(float(x.corr().iloc[0, 1]), 3), "Sharpe cme / proxy 2020-22": [sh(x.cme.loc[:"2022"]), sh(x.proxy.loc[:"2022"])],
            "Sharpe cme / proxy 2023-26": [sh(x.cme.loc["2023":]), sh(x.proxy.loc["2023":])]})
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cxb_proxy_check.json").write_text(json.dumps(out, indent=1))
