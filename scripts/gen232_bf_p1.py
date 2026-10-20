"""Gen232 (config/gen232_protocol.json): P1 long-only IBS on US100/US500 CFDs at 16:00 ET in the bf index sleeve. Writes results/gen232.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen147_cfd_r1.py")}; exec(open(ROOT / "scripts/gen147_cfd_r1.py").read().split("P6 = p6()")[0], g)
CS, HB0, per, sh, IDXbf, p6, r1, hourly = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "p6", "r1", "hourly"))


def p1(cost=1e-4):
    legs = []
    for s in ("US100", "US500"):
        x = hourly(s); et = x.index.tz_localize("UTC").tz_convert("America/New_York"); d = pd.Series(pd.DatetimeIndex(et.date), index=x.index)
        wk = et.weekday < 5; snap = wk & (et.hour == 15); rth = wk & (et.hour >= 9) & (et.hour <= 15)
        c = x.close[snap].groupby(d[snap]).last(); hi = x.high[rth].groupby(d[rth]).max().reindex(c.index); lo = x.low[rth].groupby(d[rth]).min().reindex(c.index)
        sig = 0.25 * (((c - lo) / (hi - lo)) < 0.3).astype(float).where(hi > lo, 0.0)
        start = pd.Series(sig.to_numpy(), index=x.index[snap][~d[snap].duplicated(keep="last").to_numpy()] + pd.Timedelta(hours=1))
        r = x.close.reindex(IDXbf).ffill(limit=72).pct_change().fillna(0.0)
        wh = start.reindex(IDXbf.union(start.index)).ffill().reindex(IDXbf).fillna(0.0)
        legs.append(wh * r - wh.diff().abs().fillna(0.0) * cost)
    return sum(legs)


P6, R1, P1 = p6(), r1(1e-4), p1()
ref = CS.portfolio_v5(pd.concat([HB0, (P6 + R1).rename("vol-managed indices")], axis=1).fillna(0.0))[0]; B0, k0 = sh(ref, "2022-01-01", "2026-09-30"), per(ref, "2022-01-01")
vb = CS.portfolio_v5(pd.concat([HB0, (P6 + R1 + P1).rename("vol-managed indices")], axis=1).fillna(0.0))[0]; B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
p = per(P1, "2020-01-01")
out = {"reference": [round(B0, 3), np.round(k0, 3).tolist()], "P1 leg D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen232.json", "w"), indent=1)
if out["pass"]:
    vb.to_frame("book").to_parquet(ROOT / "results/gen232_book.parquet")
