"""Gen190 (config/gen190_protocol.json): weight caps / equal weights, walk-forward selection. Writes results/gen190.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)


def cap(w, c):
    w = w / w.sum()
    for _ in range(50):
        over = w > c
        if not over.any():
            break
        ex = (w[over] - c).sum(); w[over] = c; w[~over] += ex * w[~over] / w[~over].sum()
    return w


def weights(T, m):
    sr = T.mean() / T.std(); sd = T.std(); pos = sr > 0
    if m == "SW":
        w = sr.clip(lower=0) / sd
    elif m.startswith("CAP"):
        return cap((sr.clip(lower=0) / sd), int(m[3:]) / 100)
    elif m == "EQR":
        w = (1 / sd).where(pos, 0.0)
    else:
        w = pos.astype(float)
    return w / w.sum()


def book(end, m):
    w = weights(P.loc[:end], m); raw = (P * w).sum(axis=1)
    lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


M = ["SW", "CAP20", "CAP12", "EQR", "EW"]
sel = {m: round(F.sharpe(book("2017-12-31", m), "2018-01-01", "2022-12-31"), 3) for m in M}
ch = max(sel, key=sel.get); b = book("2022-12-31", ch)
out = {"walk-forward 2018-22": sel, "chosen": ch, "book 2023-26": round(F.sharpe(b, "2023-01-01", "2026-09-30"), 3),
       "reference SW": round(F.sharpe(book("2022-12-31", "SW"), "2023-01-01", "2026-09-30"), 3), "weights": weights(P.loc[:"2022-12-31"], ch).round(3).to_dict()}
out["adopt"] = bool(ch != "SW" and out["book 2023-26"] > 1.137)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen190.json", "w"), indent=1)
