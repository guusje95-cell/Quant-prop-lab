"""Writes results/v99/cx_solxrp_prefix.parquet (F-CX4 SOL / XRP legs, research data to 2026-09-30) with the LIVE code
(qpl.live.futures_cx.proxy_hourly) and checks that the futures + CX4 book reproduces F-CX4 (0 trials)."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import crypto_sleeves as CS
import futures_db as F
from qpl.lab import binance_pack as B
from qpl.live import futures_cx as FX

c = list(FX.LEGS4); px = B.panel("close", "1h", c).loc[:"2026-09-30 23:00"]
w = CS.cstar_weights()[c]; w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
pos = w.reindex(px.index.floor("D")).set_axis(px.index).fillna(0.0)
legs = FX.daily(FX.proxy_hourly(pos, px, CS._funding_hourly(c, px.index), cost=lambda k, p: FX.LEGS4[k] / 1e4))
legs.to_frame("legs").to_parquet(FX.PREFIX4)
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P["CX"] = pd.read_parquet(FX.PREFIX)["CX"].add(legs, fill_value=0.0).reindex(P.index).fillna(0.0)
print([round(F.sharpe(FX.book(P)[0], *s), 3) for s in F.SPLITS])
