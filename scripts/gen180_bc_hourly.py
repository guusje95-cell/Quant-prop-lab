"""Gen180 (config/gen180_protocol.json): hourly big-move continuation in ZF/ZN/ZB. Writes results/gen180.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
F, S, TUNE, JUDGE, D = (h[k] for k in ("F", "S", "TUNE", "JUDGE", "D"))
ROOTS = ["ZF", "ZN", "ZB"]; HR = {}
for r in ROOTS:
    f = F.front(r); x = f.r.astype(float); td = pd.Series(F.trade_date(f.index), index=f.index)
    sd = x.rolling(20 * 23, min_periods=200).std().shift(1)
    dv = (x.groupby(td).sum().rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)
    HR[r] = (x, td, x / sd, dv.reindex(td.to_numpy()).set_axis(x.index), F.cost_frac(r, f.close.astype(float)))


def sleeve(th, H):
    out = []
    for r in ROOTS:
        x, td, z, dv, cost = HR[r]
        trig = pd.Series(np.where(z.abs() > th, np.sign(x), np.nan), index=x.index)
        pos = trig.shift(1).ffill(limit=H - 1).fillna(0.0)                 # from the next bar, H bars
        w = pos * 0.10 / dv / len(ROOTS); w = w.where(np.isfinite(w), 0.0)
        p = w * x.fillna(0.0) - w.diff().abs().fillna(0.0) * cost
        out.append(p.groupby(td).sum())
    p = pd.concat(out, axis=1).fillna(0.0).sum(axis=1); return p[p.index.weekday < 5]


res = []
for th in (3, 4):
    for H in (6, 24):
        p = sleeve(th, H); res.append((S(p, TUNE), {"th": th, "H": H}, p)); print(th, H, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["BCH"] = p
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen180_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen180.json", "w"), indent=1)
