"""Gen168 (config/gen168_protocol.json): bf with one merged index sleeve (P6 + R1 CFD and/or calendar). Writes results/gen168.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen147_cfd_r1.py")}; exec(open(ROOT / "scripts/gen147_cfd_r1.py").read().split("P6 = p6()")[0], g)
CS, HB0, per, sh, IDXbf, p6, r1, hourly = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "p6", "r1", "hourly"))
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], c)
cal = pd.concat(c["M"].values(), axis=1).max(axis=1)                 # union of T1, T2, FC, MM on futures trade dates (ET)
cal_days = set(cal[cal > 0].index)


def calendar():
    eh = IDXbf.tz_localize("UTC").tz_convert("America/New_York")
    td = pd.DatetimeIndex(eh.date) + pd.to_timedelta((eh.hour >= 17).astype(int), unit="D")
    on = pd.Series(td.isin(list(cal_days)).astype(float), index=IDXbf)
    legs = []
    for s in ("US100", "US500"):
        r = hourly(s)["close"].reindex(IDXbf).ffill(limit=72).pct_change().fillna(0.0); w = 0.5 * on
        legs.append(w * r - w.diff().abs().fillna(0.0) * 1e-4)
    return sum(legs)


P6 = p6(); R1 = r1(1e-4); CAL = calendar()
base = CS.portfolio_v5(pd.concat([HB0, P6.rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B0, k0 = sh(base, "2022-01-01", "2026-09-30"), per(base, "2022-01-01")
out = {"bf + P6": [round(B0, 3), np.round(k0, 3).tolist()], "calendar leg D/T/H": np.round(per(CAL, "2020-01-01"), 3).tolist()}
for name, sl in {"M1": P6 + R1, "M2": P6 + CAL, "M3": P6 + R1 + CAL}.items():
    vb = CS.portfolio_v5(pd.concat([HB0, sl.rename("vol-managed indices")], axis=1).fillna(0.0))[0]
    B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
    out[name] = {"sleeve D/T/H": np.round(per(sl, "2020-01-01"), 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
                 "pass": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
    print(name, out[name], flush=True)
    vb.to_frame("book").to_parquet(ROOT / f"results/gen168_{name}_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen168.json", "w"), indent=1)
