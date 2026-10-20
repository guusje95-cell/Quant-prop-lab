"""Gen192 (config/gen192_protocol.json): BC trigger window / universe. Writes results/gen192.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B


def bc(members, win, th=2.0, H=3):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); R = R[R.index.weekday < 5]
    sd = R.rolling(60, min_periods=40).std().shift(1); x = R.rolling(win).sum(); z = x / (sd * np.sqrt(win))
    sig = pd.DataFrame(np.where(z.abs() > th, np.sign(x), 0.0), index=R.index, columns=members)
    pos = sig.shift(1).rolling(H, min_periods=1).mean()
    W = pos * 0.10 / (sd * np.sqrt(252)) / len(members)
    return daily_book(W.shift(1).fillna(0.0).where(np.isfinite, 0.0), members)


res = []
for win in (1, 3):
    for uni in (("ZF", "ZN", "ZB"), ("ZT", "ZF", "ZN", "ZB")):
        p = bc(list(uni), win); res.append((S(p, TUNE), {"win": win, "uni": "+".join(uni)}, p)); print(win, uni, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
cur = res[0]; res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"grid": [(round(a, 3), b) for a, b, _ in res], "chosen": prm, "current check (should equal Gen163 BC)": round(cur[0], 3)}
if prm != {"win": 1, "uni": "ZF+ZN+ZB"}:
    out.update(B.judge({"BC": p}, "gen192"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen192.json", "w"), indent=1)
