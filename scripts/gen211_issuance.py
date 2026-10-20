"""Gen211 (config/gen211_protocol.json): issuance hedging pressure in Treasuries. Writes results/gen211.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen193_qe_cny.py")}; exec(open(ROOT / "scripts/gen193_qe_cny.py").read().split("\ndef qd(")[0], g)
F, S, TUNE, JUDGE, book, B = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "book", "B"))
BD = ["ZF", "ZN", "ZB"]


def dw(ix):
    return pd.Series(ix.weekday.isin([2, 3, 4]).astype(float), index=ix)


def is3(ix):
    m = pd.Series(0.0, index=ix)
    for _, gg in ix.to_series().groupby(ix.to_period("M")):
        m.loc[gg.index[:3]] = 1.0
    return m


FAM = {"DW": book(BD, dw, 1.0), "IS": book(BD, is3, -1.0)}
rep, enter = {}, {}
for n, p in FAM.items():
    s = S(p, TUNE); rep[n] = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
    print(n, rep[n], flush=True)
    if s > 0.3:
        enter[n] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    out.update(B.judge(enter, "gen211"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen211.json", "w"), indent=1)
