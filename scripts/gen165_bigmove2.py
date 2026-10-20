"""Gen165 (config/gen165_protocol.json): big-move continuation, equity up-days and FX. Writes results/gen165.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D, daily_book = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))


def sleeve(members, th, H, up_only=False):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); R = R[R.index.weekday < 5]
    sd = R.rolling(60, min_periods=40).std().shift(1); z = R / sd
    sig = pd.DataFrame(np.where((z > th) if up_only else (z.abs() > th), np.sign(R), 0.0), index=R.index, columns=members)
    pos = sig.shift(1).rolling(H, min_periods=1).mean()                    # traded at the next close, held H days
    W = pos * 0.10 / (sd * np.sqrt(252)) / len(members)
    return daily_book(W.shift(1).fillna(0.0).where(np.isfinite, 0.0), members)


FAM = {"EU": ["ES", "NQ", "RTY", "YM"], "FX": ["6E", "6J", "6B", "6A", "6C", "6S"]}
rep, enter = {}, {}
for name, mem in FAM.items():
    res = []
    for th in (1.5, 2.0):
        for H in (1, 3, 5):
            p = sleeve(mem, th, H, up_only=(name == "EU")); res.append((S(p, TUNE), {"th": th, "H": H}, p)); print(name, th, H, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
    res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
    rep[name] = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
    if s > 0.3:
        enter[name] = p
out = {"families": rep, "entered": list(enter)}
if enter:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n, p in enter.items():
        base[n] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.041)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen165_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen165.json", "w"), indent=1)
