"""Gen203 (config/gen203_protocol.json): equity timing sleeves on 4 indices vs ES+NQ. Writes results/gen203.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, D, daily_book, PX, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "D", "daily_book", "PX", "monthly"))
k = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], k)
M = dict(k["M"]); M["OIL"] = monthly(np.sign(PX("CL") / PX("CL").shift(21) - 1), lambda v: 1.0 if v < 0 else 0.0)
import fbook as B
U = {"ALL4": (["ES", "NQ", "RTY", "YM"], 0.25), "ESNQ": (["ES", "NQ"], 0.5)}


def sleeves(u):
    mem, sz = U[u]; return {n: daily_book(pd.DataFrame({r: m.reindex(IX).fillna(0.0) * sz for r in mem}), mem) for n, m in M.items()}


res = {}
for u in U:
    sl = sleeves(u); comb = pd.DataFrame(sl).fillna(0.0).sum(axis=1)
    res[u] = {"tune": round(S(comb, TUNE), 3), "per sleeve tune": {n: round(S(p, TUNE), 2) for n, p in sl.items()}, "sl": sl}; print(u, res[u]["tune"], res[u]["per sleeve tune"], flush=True)
ch = max(U, key=lambda u: res[u]["tune"]); out = {"variants": {u: {kk: v for kk, v in res[u].items() if kk != "sl"} for u in U}, "chosen": ch}
if ch == "ESNQ":
    base = B.sleeves(); chk = {n: round(S(base[n], TUNE), 3) for n in M}; out["current sleeves tune (check)"] = chk
    out.update(B.judge(res[ch]["sl"], "gen203"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen203.json", "w"), indent=1)
