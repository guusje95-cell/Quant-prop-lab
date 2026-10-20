"""Gen156 (config/gen156_protocol.json): book construction with correlations, walk-forward selection. Writes results/gen156.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
S = lambda p, a, b: F.sharpe(p, a, b)


def weights(T, m):
    mu, sd, C = T.mean(), T.std(), T.cov()
    if m == "SW":
        w = (mu / sd).clip(lower=0) / sd
    elif m.startswith("MV"):
        lam = int(m[2:]) / 100; Cs = (1 - lam) * C + lam * np.diag(np.diag(C))
        w = pd.Series(np.linalg.solve(Cs.to_numpy(), mu.to_numpy()), index=T.columns).clip(lower=0)
    elif m == "SWC":
        R = T.corr(); mc = (R.sum() - 1) / (len(R) - 1)
        w = (mu / sd).clip(lower=0) / sd / (1 + mc.clip(lower=0))
    else:  # HRP
        R = T.corr().fillna(0); dist = np.sqrt(((1 - R) / 2).clip(lower=0)); order = list(T.columns[leaves_list(linkage(squareform(dist.to_numpy(), checks=False), "single"))])
        w = pd.Series(1.0, index=order); clusters = [order]
        while clusters:
            nxt = []
            for c in clusters:
                if len(c) < 2:
                    continue
                a, b = c[:len(c) // 2], c[len(c) // 2:]
                va = lambda k: (lambda iv: float(iv @ C.loc[k, k].to_numpy() @ iv))((1 / np.diag(C.loc[k, k])) / (1 / np.diag(C.loc[k, k])).sum())
                al = 1 - va(a) / (va(a) + va(b)); w[a] *= al; w[b] *= 1 - al; nxt += [a, b]
            clusters = nxt
        w = w.reindex(T.columns)
    return w / w.sum()


def book(w):
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


M = ["SW", "MV50", "MV80", "HRP", "SWC"]
sel = {m: round(S(book(weights(P.loc[:"2017-12-31"], m)), "2018-01-01", "2022-12-31"), 3) for m in M}
ch = max(sel, key=sel.get); wfin = weights(P.loc[:"2022-12-31"], ch); b = book(wfin)
out = {"walk-forward 2018-22 (weights 2010-17)": sel, "chosen": ch, "weights 2010-22": wfin.round(3).to_dict(),
       "book 2023-26": round(S(b, "2023-01-01", "2026-09-30"), 3), "reference SW 2023-26": round(S(book(weights(P.loc[:"2022-12-31"], "SW")), "2023-01-01", "2026-09-30"), 3)}
out["adopt"] = bool(ch != "SW" and out["book 2023-26"] > 0.842)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen156.json", "w"), indent=1)
