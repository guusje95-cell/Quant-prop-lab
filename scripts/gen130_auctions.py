"""Gen130 (config/gen130_protocol.json): Treasury auction cycle in ZT/ZF/ZN/ZB futures. Writes results/gen130.csv."""
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

a = pd.read_parquet(ROOT / "research_data/more2/treasury_auctions.parquet")
a = a[a.securityType.isin(["Note", "Bond"])].copy(); a["date"] = pd.to_datetime(a.auctionDate)


def root_of(t, term):
    if t == "Note" and term == "2-Year":
        return "ZT"
    if t == "Note" and term == "5-Year":
        return "ZF"
    if t == "Note" and (term.startswith("10-Year") or term.startswith("9-Year")):
        return "ZN"
    if t == "Bond" and (term.startswith("30-Year") or term.startswith("29-Year")):
        return "ZB"
    return None


a["root"] = [root_of(t, s) for t, s in zip(a.securityType, a.securityTerm)]
a = a.dropna(subset=["root"])
print(a.groupby("root").size().to_dict(), flush=True)
M = ["ZT", "ZF", "ZN", "ZB"]; R = pd.DataFrame({r: D[r].r for r in M}).sort_index(); idx = R.index
vol = R.rolling(60).std() * np.sqrt(252)
W1 = pd.DataFrame(0.0, index=idx, columns=M); W2 = W1.copy()
for _, e in a.iterrows():
    if e.date not in idx:
        continue
    i = idx.get_loc(e.date)
    if i < 6 or i + 4 >= len(idx):
        continue
    s = 0.10 / vol[e.root].iloc[i - 5]
    if not np.isfinite(s):
        continue
    W1.loc[idx[i - 4:i], e.root] = -s                       # held during days t-4..t-1 (decided at the close of t-5)
    W2.loc[idx[i + 1:i + 5], e.root] = s                    # held during days t+1..t+4 (decided at the auction-day close)
report("A1 pre-auction cheapening (short)", daily_book(W1, M), "multi-day (MFFU/Tradeify)")
report("A2 post-auction recovery (long)", daily_book(W2, M), "multi-day")
report("A3 round trip", daily_book(W1 + W2, M), "multi-day")
pd.DataFrame(rows).to_csv(ROOT / "results/gen130.csv", index=False)

pd.DataFrame(g["PNL"]).to_parquet(ROOT / "results/gen130_daily.parquet")
