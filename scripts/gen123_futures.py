"""Gen123 (config/gen123_protocol.json): TSMOM, in-session vol-managed equity, risk parity. Writes results/gen123.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen122_futures.py").read()
g = {"__file__": str(ROOT / "scripts/gen122_futures.py")}
exec(src[:src.index("# F1 / F2")] + src[src.index("# daily helpers"):src.index("# F3")], g)
D, daily_book, report, hourly_pnl, rows = (g[k] for k in ("D", "daily_book", "report", "hourly_pnl", "rows"))


def stats(p):
    p = p[p.index.weekday < 5]; eq = (1 + p).cumprod()
    return {"ann ret": round(float(p.mean() * 252), 3), "ann vol": round(float(p.std() * np.sqrt(252)), 3), "maxDD": round(float((eq / eq.cummax() - 1).min()), 3)}


roots = F.NONCRYPTO; R = pd.DataFrame({r: D[r].r for r in roots}).sort_index()
# G1
vol = R.ewm(span=60, min_periods=40).std() * np.sqrt(252); px = (1 + R.fillna(0.0)).cumprod()
W = pd.DataFrame(np.nan, index=R.index, columns=roots)
for d in R.index.to_series().groupby(R.index.to_period("M")).max():
    i = R.index.get_loc(d)
    if i < 260:
        continue
    s = np.sign(px.iloc[i] / px.iloc[i - 252] - 1); live = vol.loc[d].notna() & R.loc[:d].notna().iloc[-252:].all()
    W.loc[d] = (s * 0.40 / vol.loc[d]).where(live, 0.0) / live.sum()
W1 = W.ffill().fillna(0.0).shift(1).fillna(0.0)
p1 = daily_book(W1, roots); report("G1 TSMOM 12m (24 markets)", p1, "multi-day (MFFU/Tradeify)"); rows[-1].update(stats(p1))
# G2
E = ["ES", "NQ"]; RE = pd.DataFrame({r: D[r].r for r in E}).sort_index(); rv = RE.rolling(20).std() * np.sqrt(252)
W5 = (0.5 * (0.15 / rv).clip(upper=2.0)).shift(1).fillna(0.0)
P = {}
for r in E:
    f = F.front(r); t = F.ny(f.index); w = W5[r].reindex(F.trade_date(f.index)).to_numpy()
    P[r] = pd.Series(np.where(t.h.isin([16, 17]), 0.0, w), index=f.index).fillna(0.0)
p2 = hourly_pnl(P); report("G2 vol-managed ES/NQ in-session only", p2, "in-session (Topstep/Lucid OK)"); rows[-1].update(stats(p2))
# G3
M = ["ES", "ZN", "GC"]; RM = pd.DataFrame({r: D[r].r for r in M}).sort_index(); v60 = RM.rolling(60).std() * np.sqrt(252)
w = (1 / v60).div((1 / v60).sum(axis=1), axis=0)
raw = (w.shift(1) * RM).sum(axis=1); lvl = (0.10 / (raw.rolling(60).std() * np.sqrt(252))).clip(upper=3).shift(1)
W3 = w.shift(1).mul(lvl, axis=0).fillna(0.0)
p3 = daily_book(W3, M); report("G3 risk parity ES/ZN/GC", p3, "multi-day (MFFU/Tradeify)"); rows[-1].update(stats(p3))
bh = daily_book(pd.DataFrame(W3.mean().to_dict(), index=RM.index), M); k = F.splits(bh)
print("G3 beta check: buy-and-hold at G3's average weights", k, stats(bh))
pd.DataFrame(rows).to_csv(ROOT / "results/gen123.csv", index=False)
