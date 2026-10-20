"""Gen175 (config/gen175_protocol.json): international R1 legs in the merged bf index sleeve. Writes results/gen175.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen147_cfd_r1.py")}; exec(open(ROOT / "scripts/gen147_cfd_r1.py").read().split("P6 = p6()")[0], g)
CS, HB0, per, sh, IDXbf, p6, r1, hourly, rsi2 = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "p6", "r1", "hourly", "rsi2"))
SPEC = {"DE40": ("Europe/Berlin", 9, 15), "EU50": ("Europe/Berlin", 9, 15), "UK100": ("Europe/London", 9, 15), "JP225": ("Asia/Tokyo", 9, 13)}


def leg(s, cost=1e-4):
    tz, h0, hs = SPEC[s]; x = hourly(s); lt = x.index.tz_localize("UTC").tz_convert(tz); d = pd.Series(pd.DatetimeIndex(lt.date), index=x.index)
    wk = lt.weekday < 5; snap = wk & (lt.hour == hs); rth = wk & (lt.hour >= h0) & (lt.hour <= hs)
    c = x.close[snap].groupby(d[snap]).last(); hi = x.high[rth].groupby(d[rth]).max().reindex(c.index); lo = x.low[rth].groupby(d[rth]).min().reindex(c.index)
    ibs = (c - lo) / (hi - lo)
    ind = [(rsi2(c) < 10), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
    sig = 0.25 * (sum(z.astype(float) for z in ind) / 4).where(hi > lo, 0.0)
    start = pd.Series(sig.to_numpy(), index=x.index[snap][~d[snap].duplicated(keep="last").to_numpy()] + pd.Timedelta(hours=1))
    r = x.close.reindex(IDXbf).ffill(limit=72).pct_change().fillna(0.0)
    wh = start.reindex(IDXbf.union(start.index)).ffill().reindex(IDXbf).fillna(0.0)
    return wh * r - wh.diff().abs().fillna(0.0) * cost


P6 = p6(); R1 = r1(1e-4); legs = {s: leg(s) for s in SPEC}; INT = sum(legs.values())
ref = CS.portfolio_v5(pd.concat([HB0, (P6 + R1).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B0, k0 = sh(ref, "2022-01-01", "2026-09-30"), per(ref, "2022-01-01")
vb = CS.portfolio_v5(pd.concat([HB0, (P6 + R1 + INT).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01"); p = per(INT, "2020-01-01")
out = {"reference bf + (P6 + R1)": [round(B0, 3), np.round(k0, 3).tolist()], "per index D/T/H": {s: np.round(per(l, "2020-01-01"), 3).tolist() for s, l in legs.items()},
       "international leg D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen175.json", "w"), indent=1)
if out["pass"]:
    vb.to_frame("book").to_parquet(ROOT / "results/gen175_book.parquet")
