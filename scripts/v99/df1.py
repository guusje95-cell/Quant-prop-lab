"""DF-1 (research/v99/df1_protocol.json). Writes results/v99/df1.json and results/v99/df1_sleeves.parquet."""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat
F = dailyflat.patch()
src = (ROOT / "scripts/futures_book_build.py").read_text().split("\nb = B.build(P)")[0]
gb = {"__file__": str(ROOT / "scripts/futures_book_build.py"), "__name__": "fbb"}
exec(compile(src, "futures_book_build.py", "exec"), gb)
P = gb["P"]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec((ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0], g)
import basket_live as BL
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
from qpl.live import futures_cx as FX

per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
# CX (BTC / ETH C* legs) and CXB (basket) on CME, Topstep variant (c) on the patched bars
cx = FX.daily(g["execute"](g["SLEEVES"]["S6 C* BTC/ETH legs"], "c"))
_, W = BL.basket(pd.date_range("2019-06-01", "2026-09-30 23:00", freq="h"))
bw = sum(w.reindex(columns=["BTC", "ETH"]).fillna(0.0) for w in W.values())
cxb = FX.daily(g["execute"](g["d2h"](bw), "c"))
# SOL / XRP legs (Binance proxy), flat 16:00-18:00 ET and Fri 16:00 -> Sun 18:00 ET
c2 = list(FX.LEGS4); px = B.panel("close", "1h", c2).loc[:"2026-09-30 23:00"]
w = CS.cstar_weights()[c2]; w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
pos = w.reindex(px.index.floor("D")).set_axis(px.index).fillna(0.0)
et = pd.DatetimeIndex(px.index).tz_localize("UTC").tz_convert("America/New_York")
off = ((et.hour >= 16) & (et.hour < 18)) | (et.weekday == 5) | ((et.weekday == 4) & (et.hour >= 16)) | ((et.weekday == 6) & (et.hour < 18))
pos[off] = 0.0
legs = FX.daily(FX.proxy_hourly(pos, px, CS._funding_hourly(c2, px.index), cost=lambda k, p: FX.LEGS4[k] / 1e4))
Q = P.copy(); Q["CX4"] = cx.add(legs, fill_value=0.0).reindex(Q.index).fillna(0.0); Q["CXB"] = cxb.reindex(Q.index).fillna(0.0)
Q.to_parquet(ROOT / "results/v99/df1_sleeves.parquet")
import fbook
ref = fbook.build(P); cand = fbook.build(Q)
old = pd.read_parquet(ROOT / "results/futures_book_rebuild_dailyflat.parquet")["book"]
out = {"approx daily-flat book (earlier, gaps earned)": per(old), "EXACT daily-flat book, 15 sleeves (reference)": per(ref),
       "candidate + CX4 + CXB (daily-flat)": per(cand),
       "sleeves 2010-17 / 2018-22 / 2023-26 (exact daily-flat)": {c: per(Q[c]) for c in Q.columns}}
out["pass"] = bool(out["candidate + CX4 + CXB (daily-flat)"][2] >= out["EXACT daily-flat book, 15 sleeves (reference)"][2] + 0.05
                   and out["candidate + CX4 + CXB (daily-flat)"][1] >= out["EXACT daily-flat book, 15 sleeves (reference)"][1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df1.json").write_text(json.dumps(out, indent=1))
