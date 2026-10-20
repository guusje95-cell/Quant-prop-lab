"""Gen225 (config/gen225_protocol.json): long Treasuries after VIX term-structure inversion. Writes results/gen225.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen193_qe_cny.py")}; exec(open(ROOT / "scripts/gen193_qe_cny.py").read().split("\ndef qd(")[0], g)
F, S, TUNE, JUDGE, book, B = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "book", "B"))
M2 = ROOT / "research_data/more2"
vix = pd.read_parquet(M2 / "vix_VIX.parquet")["close"]; v3 = pd.read_parquet(M2 / "vix_VIX3M.parquet")["close"]
inv = ((v3 / vix - 1) < 0).astype(float)


def mk(H):
    return lambda ix: inv.reindex(ix).ffill().fillna(0.0).shift(1).rolling(H, min_periods=1).max().fillna(0.0)


res = []
for H in (5, 21):
    p = book(["ZF", "ZN", "ZB"], mk(H), 1.0); res.append((S(p, TUNE), H, p)); print(H, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, H, p = res[0]
out = {"best H": H, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "time invested": round(float((p != 0).mean()), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"VTB": p}, "gen225"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen225.json", "w"), indent=1)
