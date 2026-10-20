"""Gen221 (config/gen221_protocol.json): sleeve-level vol targeting of always-active sleeves, walk-forward. Writes results/gen221.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
P0 = B.sleeves(); P0 = P0[P0.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
ACT = ["F5", "G1", "A3", "U5"]


def svt(P, fit_end):
    P = P.copy()
    for c in ACT:
        sd = P[c].rolling(60, min_periods=40).std().shift(1); ref = P[c].loc[:fit_end].std()
        P[c] = P[c] * (ref / sd).clip(upper=2).fillna(1.0)
    return P


def book(P, fit_end):
    T = P.loc[:fit_end]; w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); return (raw * lvl).dropna()


sel = {"RAW": round(F.sharpe(book(P0, "2017-12-31"), "2018-01-01", "2022-12-31"), 3), "SVT": round(F.sharpe(book(svt(P0, "2017-12-31"), "2017-12-31"), "2018-01-01", "2022-12-31"), 3)}
ch = max(sel, key=sel.get); out = {"walk-forward 2018-22": sel, "chosen": ch}
if ch == "SVT":
    b = book(svt(P0, "2022-12-31"), "2022-12-31"); out["book 2023-26"] = round(F.sharpe(b, *B.JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > B.REF)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen221.json", "w"), indent=1)
