"""Gen195 (config/gen195_protocol.json): gold autumn effect, yen fiscal-year-end. Writes results/gen195.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen193_qe_cny.py")}; exec(open(ROOT / "scripts/gen193_qe_cny.py").read().split("\ndef qd(")[0], g)
F, S, TUNE, JUDGE, book, B = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "book", "B"))
win = lambda a, b: (lambda ix: pd.Series((((ix.month * 100 + ix.day) >= a) & ((ix.month * 100 + ix.day) <= b)).astype(float), index=ix))
FAM = {"GA": book(["GC"], win(901, 1130), 1.0), "JR": book(["6J"], win(215, 331), 1.0)}
rep, enter = {}, {}
for n, p in FAM.items():
    s = S(p, TUNE); rep[n] = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
    print(n, rep[n], flush=True)
    if s > 0.3:
        enter[n] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    out.update(B.judge(enter, "gen195"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen195.json", "w"), indent=1)
