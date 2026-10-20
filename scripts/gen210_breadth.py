"""Gen210 (config/gen210_protocol.json): BC + UB/TN; equity timing sleeves + NKD. Needs the extra Databento roots. Writes results/gen210.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
DB = ROOT / "research_data/databento"
have = {r for r in ("UB", "TN", "NKD") if (DB / f"{r}_1h.parquet").exists()}
if not have:
    sys.exit("no extra roots yet (get_futures_extra.bat)")
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, daily_book, PX, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "daily_book", "PX", "monthly"))
D = {r: F.daily(r) for r in ["ZF", "ZN", "ZB", "ES", "NQ", "CL"] + sorted(have)}
c["D"].update(D)                                                          # daily_book reads D from the gen127 namespace
import fbook as B
rep, changes = {}, {}


def bc(members, th=2.0, H=3):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); R = R[R.index.weekday < 5]
    sd = R.rolling(60, min_periods=40).std().shift(1); z = R / sd
    sig = pd.DataFrame(np.where(z.abs() > th, np.sign(R), 0.0), index=R.index, columns=members)
    W = sig.shift(1).rolling(H, min_periods=1).mean() * 0.10 / (sd * np.sqrt(252)) / len(members)
    return daily_book(W.shift(1).fillna(0.0).where(np.isfinite, 0.0), members)


rb = [r for r in ("UB", "TN") if r in have]
if rb:
    cur, ext = bc(["ZF", "ZN", "ZB"]), bc(["ZF", "ZN", "ZB"] + rb)
    t = {"current": round(S(cur, TUNE), 3), "with " + "+".join(rb): round(S(ext, TUNE), 3)}; rep["BC+"] = t
    if t["with " + "+".join(rb)] > t["current"]:
        changes["BC"] = ext
if "NKD" in have:
    k = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], k)
    M = dict(k["M"]); M["OIL"] = monthly(np.sign(PX("CL") / PX("CL").shift(21) - 1), lambda v: 1.0 if v < 0 else 0.0)

    def sleeves(mem):
        sz = 1.0 / len(mem); return {n: daily_book(pd.DataFrame({r: m.reindex(IX).fillna(0.0) * sz for r in mem}), mem) for n, m in M.items()}
    a, b = sleeves(["ES", "NQ"]), sleeves(["ES", "NQ", "NKD"])
    ca, cb = pd.DataFrame(a).fillna(0.0).sum(axis=1), pd.DataFrame(b).fillna(0.0).sum(axis=1)
    t = {"ES+NQ": round(S(ca, TUNE), 3), "ES+NQ+NKD": round(S(cb, TUNE), 3), "appraisal ES+NQ+NKD": round(B.appraisal(cb), 3)}; rep["NKD"] = t
    if t["ES+NQ+NKD"] > t["ES+NQ"] and t["appraisal ES+NQ+NKD"] > 0.3:
        changes.update(b)
out = {"have": sorted(have), "families": rep, "changes": list(changes)}
if changes:
    out.update(B.judge(changes, "gen210"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen210.json", "w"), indent=1)
