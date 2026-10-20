"""Gen178 (config/gen178_protocol.json): earnings-season months and lunar cycle. Writes results/gen178.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen159_fomc_cycle.py")}; exec(open(ROOT / "scripts/gen159_fomc_cycle.py").read().split("FAM = {")[0], c)
F, S, TUNE, JUDGE, h, IX, sleeve = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "IX", "sleeve"))
EM = IX.month.isin([1, 4, 7, 10])
ref = pd.Timestamp("2000-01-06 18:14"); syn = 29.530588
age = ((IX + pd.Timedelta(hours=16) - ref) / pd.Timedelta(days=1)) % syn
lunar = np.minimum(age, syn - age) <= 7
FAM = {"EA": [(lambda: sleeve(np.asarray(EM)), {"v": "whole"}), (lambda: sleeve(np.asarray(EM & (IX.day >= 8))), {"v": "day>=8"})],
       "LU": [(lambda: sleeve(np.asarray(lunar)), {"v": "new moon +-7"})]}
rep, enter = {}, {}
for name, opts in FAM.items():
    res = []
    for fn, prm in opts:
        p = fn(); res.append((S(p, TUNE), prm, p)); print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen178_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen178.json", "w"), indent=1)
