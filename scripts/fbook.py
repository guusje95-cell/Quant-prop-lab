"""Futures book construction after Gen190: equal-risk weights (1/sd over sleeves with positive 2010-22 Sharpe), 10% vol target on
60-day realised vol (cap 3x, lagged). Shared by Gen191+ entrant tests."""
from pathlib import Path
import numpy as np
import pandas as pd
import futures_db as F
ROOT = Path(__file__).resolve().parents[1]
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
REF = 1.143                                                                  # Gen190 book 2023-26


def sleeves():
    return pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")


def build(P, fit_end="2022-12-31"):
    P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0); T = P.loc[:fit_end]
    w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


def judge(entrants, tag, ref=REF):
    """Add entrants to the current sleeves, ONE 2023-26 evaluation; saves sleeves + book if adopted."""
    base = sleeves()
    for n, p in entrants.items():
        base[n] = p
    b = build(base); out = {"book 2023-26": round(F.sharpe(b, *JUDGE), 3), "reference": ref,
                            "book 2010-17 / 2018-22": [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > ref)
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / f"results/{tag}_book.parquet")
    return out
