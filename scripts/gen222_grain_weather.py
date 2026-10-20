"""Gen222 (config/gen222_protocol.json): long grains Apr 15 - Jun 30. Writes results/gen222.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen193_qe_cny.py")}; exec(open(ROOT / "scripts/gen193_qe_cny.py").read().split("\ndef qd(")[0], g)
F, S, TUNE, JUDGE, book, B = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "book", "B"))
win = lambda ix: pd.Series((((ix.month * 100 + ix.day) >= 415) & ((ix.month * 100 + ix.day) <= 630)).astype(float), index=ix)
p = book(["ZC", "ZS", "ZW"], win, 1.0)
s = S(p, TUNE); out = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"GW": p}, "gen222"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen222.json", "w"), indent=1)
