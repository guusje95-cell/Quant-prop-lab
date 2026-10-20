"""Gen177 (config/gen177_protocol.json): book-level vol estimator, walk-forward selection. Writes results/gen177.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
EST = {"R60": lambda x: x.rolling(60, min_periods=40).std(), "R20": lambda x: x.rolling(20, min_periods=15).std(), "E30": lambda x: x.ewm(span=30, min_periods=20).std(),
       "R120": lambda x: x.rolling(120, min_periods=80).std(), "MIX": lambda x: np.maximum(x.rolling(20, min_periods=15).std(), x.rolling(60, min_periods=40).std())}


def book(end, e):
    T = P.loc[:end]; w = (T.mean() / T.std()).clip(lower=0) / T.std(); w = w / w.sum()
    raw = (P * w).sum(axis=1); lvl = (0.10 / (EST[e](raw) * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


sel = {e: round(F.sharpe(book("2017-12-31", e), "2018-01-01", "2022-12-31"), 3) for e in EST}
ch = max(sel, key=sel.get); b = book("2022-12-31", ch)
out = {"walk-forward 2018-22": sel, "chosen": ch, "book 2023-26": round(F.sharpe(b, "2023-01-01", "2026-09-30"), 3),
       "reference R60 2023-26": round(F.sharpe(book("2022-12-31", "R60"), "2023-01-01", "2026-09-30"), 3)}
out["adopt"] = bool(ch != "R60" and out["book 2023-26"] > 1.102)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen177.json", "w"), indent=1)
