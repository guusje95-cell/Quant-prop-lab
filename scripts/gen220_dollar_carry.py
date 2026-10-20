"""Gen220 (config/gen220_protocol.json): dollar carry by average forward discount. Writes results/gen220.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, D, daily_book, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "D", "daily_book", "monthly"))
import fbook as B
FX = ["6E", "6J", "6B", "6A", "6C", "6S"]
fd = pd.DataFrame({r: np.log(D[r].near_far) / F.SPEC[r][3] for r in FX}).reindex(IX)
afd = fd.mean(axis=1).rolling(21, min_periods=10).mean()
pos = monthly(afd, lambda v: 1.0 if v > 0 else -1.0)
R = pd.DataFrame({r: D[r].r for r in FX}).reindex(IX); v = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
p = daily_book((0.10 / v / 6).mul(pos, axis=0).fillna(0.0).where(np.isfinite, 0.0), FX)
s = S(p, TUNE); out = {"share of months long": round(float((pos > 0).mean()), 2), "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3),
                       "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"DC$": p}, "gen220"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen220.json", "w"), indent=1)
