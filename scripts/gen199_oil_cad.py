"""Gen199 (config/gen199_protocol.json): 6C on lagged CL returns. Writes results/gen199.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
R = pd.DataFrame({"CL": D["CL"].r, "6C": D["6C"].r}).sort_index(); R = R[R.index.weekday < 5]
v = (R["6C"].rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)


def sleeve(L):
    s = np.sign(R.CL.rolling(L).sum()).shift(1)                       # known at the close of t-1 ... traded at that close? use one more day:
    W = pd.DataFrame({"6C": (s.shift(1) * 0.10 / v)})                  # 1-day execution lag
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), ["6C"])


res = []
for L in (1, 5):
    p = sleeve(L); res.append((S(p, TUNE), {"L": L}, p)); print(L, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"OCAD": p}, "gen199"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen199.json", "w"), indent=1)
