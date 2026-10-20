"""Gen197 (config/gen197_protocol.json): hour-opening order imbalance on BTC/ETH perps. Writes results/gen197.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen171_crypto_calendar.py").read()
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(src.split("\ndays = pd.date_range")[0], g)
CS, HV7, sh, per, B0, k0 = (g[k] for k in ("CS", "HV7", "sh", "per", "B0", "k0"))
COINS = ["BTC", "ETH"]; DATA = {}
for c in COINS:
    x = CS.B.k5(c); op = x[x.index.minute == 0]
    imb = ((2 * op.taker_buy_volume - op.volume) / op.volume.replace(0, np.nan)); imb.index = imb.index.floor("h")
    z = (imb - imb.rolling(24 * 30, min_periods=24 * 10).mean().shift(1)) / imb.rolling(24 * 30, min_periods=24 * 10).std().shift(1)
    h = x.close.resample("1h").last(); r = h.pct_change(fill_method=None)
    DATA[c] = (z.reindex(h.index), r)
IDX = DATA["BTC"][1].index
FUND = CS._funding_hourly(COINS, IDX)


def sleeve(H, k):
    out = []
    for c in COINS:
        z, r = DATA[c]; s = pd.Series(np.where(z.abs() > k, np.sign(z), 0.0), index=z.index).fillna(0.0)
        w = 0.5 * s.shift(1).rolling(H, min_periods=1).sum() / H                    # first held hour = hh+1:00
        out.append(w * r.fillna(0.0) - w.diff().abs().fillna(0.0) * 5e-4 - w * FUND[c].reindex(IDX).fillna(0.0))
    return pd.concat(out, axis=1).sum(axis=1).loc[:"2026-09-30 23:00"]


res = []
for H in (4, 12):
    for k in (1, 2):
        p = sleeve(H, k); d = per(p, "2020-01-01"); res.append((d[0], {"H": H, "k": k}, p, d)); print(H, k, np.round(d, 3), flush=True)
res.sort(key=lambda x: -x[0]); _, prm, p, d = res[0]
vb = CS.portfolio_v5(pd.concat([HV7, p.rename("open imbalance")], axis=1).fillna(0.0))[0]; B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
out = {"grid D/T/H": {f"H{x[1]['H']} k{x[1]['k']}": np.round(x[3], 3).tolist() for x in res}, "chosen": prm, "v7": [round(B0, 3), np.round(k0, 3).tolist()],
       "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(d[0] > 0 and d[1] >= 0.8 and d[2] >= 0.5 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen197.json", "w"), indent=1)
