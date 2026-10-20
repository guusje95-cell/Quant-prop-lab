"""Gen160 (config/gen160_protocol.json): sleeve momentum overlay, walk-forward selection. Writes results/gen160.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
CAND = {"NONE": None, "M252h": (252, 0.5), "M252z": (252, 0.0), "M126h": (126, 0.5), "M504h": (504, 0.5)}


def book(end, cand):
    T = P.loc[:end]; w = (T.mean() / T.std()).clip(lower=0) / T.std(); w = w / w.sum()
    W = pd.DataFrame([w.to_numpy()] * len(P), index=P.index, columns=P.columns)
    if CAND[cand]:
        lb, f = CAND[cand]; tr = P.rolling(lb, min_periods=lb // 2).sum().shift(1)
        W = W * np.where(tr < 0, f, 1.0); W = W.mul(w.sum() / W.sum(axis=1).replace(0, np.nan), axis=0)
    raw = (P * W).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


sel = {c: round(F.sharpe(book("2017-12-31", c), "2018-01-01", "2022-12-31"), 3) for c in CAND}
ch = max(sel, key=sel.get); b = book("2022-12-31", ch)
out = {"walk-forward 2018-22": sel, "chosen": ch, "book 2023-26": round(F.sharpe(b, "2023-01-01", "2026-09-30"), 3),
       "reference NONE 2023-26": round(F.sharpe(book("2022-12-31", "NONE"), "2023-01-01", "2026-09-30"), 3)}
out["adopt"] = bool(ch != "NONE" and out["book 2023-26"] > 0.908)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen160.json", "w"), indent=1)
