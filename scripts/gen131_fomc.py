"""Gen131 F1 (config/gen131_protocol.json): post-FOMC drift in ZN/ZB. Writes results/gen131_fomc.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen122_futures.py").read()
g = {"__file__": str(ROOT / "scripts/gen122_futures.py")}
exec(src[:src.index("# F1 / F2")] + src[src.index("# daily helpers"):src.index("# F3")], g)
D, daily_book, report, rows = (g[k] for k in ("D", "daily_book", "report", "rows"))
fomc = pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date)
f = F.front("ZN"); t = F.ny(f.index); px = (1 + f.r).cumprod()
c13 = px[t.h == 13].groupby(t.date[t.h == 13]).last(); c15 = px[t.h == 15].groupby(t.date[t.h == 15]).last()
sig = np.sign(c15 / c13.reindex(c15.index) - 1)
M = ["ZN", "ZB"]; R = pd.DataFrame({r: D[r].r for r in M}).sort_index(); idx = R.index; vol = R.rolling(60).std() * np.sqrt(252)
W = pd.DataFrame(0.0, index=idx, columns=M); n = 0
for d in fomc:
    d = d.normalize()
    if d not in idx or d not in sig.index or not np.isfinite(sig[d]) or sig[d] == 0:
        continue
    i = idx.get_loc(d)
    for r in M:
        W.loc[idx[i + 1:i + 16], r] = sig[d] * 0.10 / vol[r].iloc[i]
    n += 1
print("FOMC events traded:", n, flush=True)
report("F1 post-FOMC drift ZN/ZB (15 days)", daily_book(W.fillna(0.0), M), "multi-day (MFFU/Tradeify)")
pd.DataFrame(rows).to_csv(ROOT / "results/gen131_fomc.csv", index=False)

pd.DataFrame(g["PNL"]).to_parquet(ROOT / "results/gen131_fomc_daily.parquet")
