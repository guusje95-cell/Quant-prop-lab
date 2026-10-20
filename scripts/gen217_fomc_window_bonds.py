"""Gen217 (config/gen217_protocol.json): long Treasuries around FOMC days. Writes results/gen217.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen193_qe_cny.py")}; exec(open(ROOT / "scripts/gen193_qe_cny.py").read().split("\ndef qd(")[0], g)
F, S, TUNE, JUDGE, book, B = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "book", "B"))
fomc = pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date).dt.normalize()


def win(ix):
    m = pd.Series(0.0, index=ix)
    for d in fomc:
        j = ix.searchsorted(d)
        if 0 < j < len(ix) and ix[j] == d:
            m.iloc[j - 1:j + 2] = 1.0
    return m


p = book(["ZF", "ZN", "ZB"], win, 1.0)
s = S(p, TUNE); out = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"FW": p}, "gen217"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen217.json", "w"), indent=1)
