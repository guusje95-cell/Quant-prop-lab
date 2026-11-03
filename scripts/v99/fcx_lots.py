"""F-CX deployment realism (0 trials): CX in WHOLE CME micro contracts (MBT / MET = 0.1 coin) at several account sizes and book risk
levels; book with the rounded CX vs the unrounded F-CXb. Writes results/v99/fcx_lots.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
import futures_db as F
from qpl.live.futures_cx import book, daily

tgt = g["SLEEVES"]["S6 C* BTC/ETH legs"]
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); P["CX"] = pd.read_parquet(ROOT / "results/v99/cx_sleeve_prefix.parquet")["CX"].reindex(P.index).fillna(0.0)
b0, W = book(P)
per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
wcx = W["CX"].reindex(pd.date_range(W.index[0], W.index[-1], freq="D")).ffill()
out = {"unrounded": per(b0)}
for acct in (50_000, 100_000, 150_000):
    for risk in (1.0, 2.0):
        cap = (wcx * acct * risk).reindex(tgt.index.floor("D")).set_axis(tgt.index).fillna(0.0)
        T = {}
        for c in ("BTC", "ETH"):
            px = g["CME"][c].close.reindex(tgt.index).ffill()
            usd = tgt[c] * cap; n = (usd / (px * 0.1)).round()
            T[c] = (n * px * 0.1 / cap.replace(0, np.nan)).fillna(0.0)
        h = g["execute"](pd.DataFrame(T), "a"); P2 = P.copy(); P2["CX"] = daily(h).reindex(P.index).fillna(0.0)
        out[f"${acct // 1000}k risk {risk}"] = per(book(P2)[0])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx_lots.json").write_text(json.dumps(out, indent=1))
