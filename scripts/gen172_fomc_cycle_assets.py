"""Gen172 (config/gen172_protocol.json): FOMC-cycle weeks 2/4/6 in Treasuries and gold. Writes results/gen172.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], c)
F, S, TUNE, JUDGE, D, daily_book, h = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book", "h"))
fc = c["M"]["FC"]


def sleeve(members):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); R = R[R.index.weekday < 5]
    v = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1); on = fc.reindex(R.index).fillna(0.0)
    return daily_book((0.10 / v / len(members)).mul(on, axis=0).fillna(0.0).where(np.isfinite, 0.0), members)


FAM = {"FB": sleeve(["ZF", "ZN", "ZB"]), "FG": sleeve(["GC"])}
rep, enter = {}, {}
for n, p in FAM.items():
    s = S(p, TUNE); rep[n] = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
    print(n, rep[n], flush=True)
    if s > 0.3:
        enter[n] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen172_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen172.json", "w"), indent=1)
