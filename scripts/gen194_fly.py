"""Gen194 (config/gen194_protocol.json): Treasury butterfly mean reversion. Writes results/gen194.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
M = ["ZT", "ZF", "ZN"]; R = pd.DataFrame({r: D[r].r for r in M}).sort_index(); R = R[R.index.weekday < 5]
V = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1); U = R / V
I = (U.ZF - 0.5 * U.ZT - 0.5 * U.ZN).fillna(0.0).cumsum()


def fly(L, th):
    z = (I - I.rolling(L).mean()) / I.rolling(L).std()
    p = (-(z / 2).clip(-1, 1)).where(z.abs() > th, 0.0).shift(1)
    W = pd.DataFrame({"ZF": p * 0.05 / V.ZF, "ZT": -p * 0.025 / V.ZT, "ZN": -p * 0.025 / V.ZN})
    return daily_book(W.fillna(0.0).where(np.isfinite, 0.0), M)


res = []
for L in (20, 60):
    for th in (1.0, 1.5):
        p = fly(L, th); res.append((S(p, TUNE), {"L": L, "th": th}, p)); print(L, th, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"FLY": p}, "gen194"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen194.json", "w"), indent=1)
