"""Gen226 (config/gen226_protocol.json): group risk parity vs EQR, walk-forward. Writes results/gen226.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import fbook as B
G = json.load(open(ROOT / "config/gen226_protocol.json"))["groups"]
P = B.sleeves(); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
bh = pd.concat([F.daily(r).r for r in ("ES", "NQ")], axis=1).mean(axis=1)


def eqr(T):
    w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); return w / w.sum()


def weights(end, kind):
    T = P.loc[:end]
    if kind == "EQR":
        return eqr(T)
    w = pd.Series(0.0, index=P.columns)
    for g, mem in G.items():
        wi = eqr(T[mem]); gv = (T[mem] * wi).sum(axis=1).std()
        if gv > 0:
            w[mem] = wi / gv
    return w / w.sum()


def book(w):
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); return (raw * lvl).dropna()


def badj(b, a, z):
    x = pd.concat([b, bh], axis=1).dropna().loc[a:z]; x = x[x.index.weekday < 5]
    be = np.cov(x.iloc[:, 0], x.iloc[:, 1])[0, 1] / x.iloc[:, 1].var(); r = x.iloc[:, 0] - be * x.iloc[:, 1]
    return round(float(r.mean() / r.std() * np.sqrt(252)), 3), round(float(x.corr().iloc[0, 1]), 2)


sel = {k: round(F.sharpe(book(weights("2017-12-31", k)), "2018-01-01", "2022-12-31"), 3) for k in ("EQR", "GRP")}
ch = max(sel, key=sel.get); w = weights("2022-12-31", ch); b = book(w)
out = {"walk-forward 2018-22": sel, "chosen": ch, "weights": w.round(3).to_dict(), "book 2023-26": round(F.sharpe(b, *B.JUDGE), 3),
       "beta-adjusted / corr 2023-26": badj(b, *B.JUDGE), "reference": B.REF}
out["adopt"] = bool(ch == "GRP" and out["book 2023-26"] > B.REF)
if ch == "GRP":
    out["GRP 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
if out["adopt"]:
    b.to_frame("book").to_parquet(ROOT / "results/gen226_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen226.json", "w"), indent=1)
