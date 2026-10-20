"""Gen120 (config/gen120_protocol.json): Deribit option flow. D1 put-skew contrarian, D2 call-minus-put buying.
Daily value = mean (skew) or sum (flows) of the 24 hours of UTC day d, used for day d+1. Writes results/gen120.csv.
--smoke: only checks data and weights (prints no performance numbers)."""
import glob
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
SMOKE = "--smoke" in sys.argv


def flow(cur):
    fs = sorted(glob.glob(str(ROOT / f"research_data/more2/deribit_{cur}_optflow_*.parquet")))
    if not fs:
        return None
    d = pd.concat([pd.read_parquet(f) for f in fs]); d["time"] = pd.to_datetime(d["time"]); d = d.set_index("time").sort_index()
    day = d.index.floor("D")
    return pd.DataFrame({"skew": (d.iv_put_otm - d.iv_call_otm).groupby(day).mean(),
                         "flow": (d.net_buy_C - d.net_buy_P).groupby(day).sum(min_count=1)})


def hold(ind, n):
    return ind.astype(float).rolling(n, min_periods=1).max()


days = pd.date_range("2020-01-01", "2026-09-30")
W1 = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]); W2 = W1.copy(); cover = {}
for c in ("BTC", "ETH"):
    f = flow(c)
    if f is None:
        continue
    f = f.reindex(days); cover[c] = (str(f.dropna().index.min().date()), str(f.dropna().index.max().date()), int(f.skew.notna().sum()))
    z1 = (f.skew - f.skew.rolling(90, min_periods=60).mean()) / f.skew.rolling(90, min_periods=60).std()
    W1[c] = (0.5 * hold(z1 > 1.5, 2) - 0.5 * hold(z1 < -1.5, 2)).fillna(0.0)
    z2 = (f.flow - f.flow.rolling(30, min_periods=20).mean()) / f.flow.rolling(30, min_periods=20).std()
    W2[c] = np.where(z2 > 1.5, 0.5, np.where(z2 < -1.5, -0.5, 0.0))
print("coverage:", cover, flush=True)
if SMOKE:
    print("smoke ok: D1 signal days", int((W1 != 0).any(axis=1).sum()), "D2 signal days", int((W2 != 0).any(axis=1).sum())); sys.exit(0)
g = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g)
g["evaluate"]("D1 put-skew contrarian (PRIMARY)", W1)
g["evaluate"]("D2 call-minus-put buying", W2)
pd.DataFrame(g["rows"]).to_csv(ROOT / "results/gen120.csv", index=False)
