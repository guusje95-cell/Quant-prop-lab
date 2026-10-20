"""Gen212 (config/gen212_protocol.json): EQR static vs yearly expanding refit. Writes results/gen212.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
P = B.sleeves(); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)


def eqr(T):
    w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); return w / w.sum()


def finish(W):
    raw = (P * W).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); return (raw * lvl).dropna()


def exp_book():
    W = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    for y in range(2013, 2027):
        W.loc[f"{y}-01-01":f"{y}-12-31"] = eqr(P.loc[:f"{y - 1}-12-31"]).to_numpy()
    return finish(W.dropna())


static17 = finish(pd.DataFrame([eqr(P.loc[:"2017-12-31"]).to_numpy()] * len(P), index=P.index, columns=P.columns))
ex = exp_book()
sel = {"STATIC": round(F.sharpe(static17, "2018-01-01", "2022-12-31"), 3), "EXP": round(F.sharpe(ex, "2018-01-01", "2022-12-31"), 3)}
ch = max(sel, key=sel.get); out = {"walk-forward 2018-22": sel, "chosen": ch, "EXP 2023-26": round(F.sharpe(ex, *B.JUDGE), 3), "reference": B.REF}
out["adopt"] = bool(ch == "EXP" and out["EXP 2023-26"] > B.REF)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen212.json", "w"), indent=1)
