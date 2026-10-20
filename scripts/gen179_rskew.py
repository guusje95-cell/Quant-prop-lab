"""Gen179 (config/gen179_protocol.json): realized skewness cross-section. Writes results/gen179.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen143_families.py")}; exec(open(ROOT / "scripts/gen143_families.py").read().split("def xs(")[0], g)
F, S, TUNE, JUDGE, build, D, daily_book, R24, SD = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build", "D", "daily_book", "R24", "SD"))
ALL = list(R24.columns)
M = {}
for r in ALL:
    f = F.front(r); td = F.trade_date(f.index); x = f.r.astype(float)
    M[r] = pd.DataFrame({"s3": (x ** 3).groupby(td).sum(), "s2": (x ** 2).groupby(td).sum(), "n": x.notna().groupby(td).sum()})
FRI = R24.index.to_series().groupby(R24.index.to_period("W")).max()


def rsk(L):
    out = {}
    for r in ALL:
        m = M[r].reindex(R24.index); s3, s2, n = (m[c].rolling(L, min_periods=L - 1).sum() for c in ("s3", "s2", "n"))
        out[r] = np.sqrt(n) * s3 / s2 ** 1.5
    return pd.DataFrame(out)


def sleeve(L, n):
    sc = rsk(L); W = pd.DataFrame(np.nan, index=R24.index, columns=ALL)
    for d in FRI:
        s = sc.loc[d].dropna()
        if len(s) < 2 * n:
            continue
        w = pd.Series(0.0, index=ALL); iv = 1 / SD.loc[d]; lo, hi = s.nsmallest(n).index, s.nlargest(n).index
        w[lo] = iv[lo]; w[hi] = -iv[hi]; W.loc[d] = w / w.abs().sum()
    return daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), ALL)


res = []
for L in (5, 21):
    for n in (4, 6):
        p = sleeve(L, n); res.append((S(p, TUNE), {"L": L, "n": n}, p)); print(L, n, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["RS"] = p
    b = build(base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen179_book.parquet")
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen179.json", "w"), indent=1)
