"""Gen136 (config/gen136_protocol.json): basis-momentum, skewness, weekly reversal, bond trend, curve trend. Writes results/gen136.csv
and results/gen136_daily.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen122_futures.py").read()
g = {"__file__": str(ROOT / "scripts/gen122_futures.py")}
exec(src[:src.index("# F1 / F2")] + src[src.index("# daily helpers"):src.index("# F3")], g)
D, daily_book, report, rows, PNL = (g[k] for k in ("D", "daily_book", "report", "rows", "PNL"))
COM = ["GC", "SI", "HG", "CL", "NG", "RB", "HO", "ZC", "ZS", "ZW", "LE", "HE"]
ALL = F.NONCRYPTO
R = pd.DataFrame({r: D[r].r for r in ALL}).sort_index(); SD = R.ewm(span=35, min_periods=30).std()


def xs_monthly(score, members, n, high_long=True):
    me = R.index.to_series().groupby(R.index.to_period("M")).max(); W = pd.DataFrame(np.nan, index=R.index, columns=members)
    for d in me:
        s = score.loc[d, members].dropna() if d in score.index else pd.Series(dtype=float)
        if len(s) < 2 * n:
            continue
        top, bot = (s.nlargest(n).index, s.nsmallest(n).index) if high_long else (s.nsmallest(n).index, s.nlargest(n).index)
        w = pd.Series(0.0, index=members); iv = 1 / SD.loc[d, members]
        w[top] = iv[top]; w[bot] = -iv[bot]; W.loc[d] = w / w.abs().sum()
    return W.ffill().fillna(0.0).shift(1).fillna(0.0)


# H1 basis-momentum
R2 = pd.DataFrame({r: F.daily_second(r) for r in COM}).reindex(R.index)
cum = lambda x: (1 + x.fillna(0.0)).rolling(252, min_periods=240).apply(np.prod, raw=True) - 1
bm = cum(R[COM]) - cum(R2)
report("H1 basis-momentum (12 commodities)", daily_book(xs_monthly(bm, COM, 4), COM), "multi-day")
# H2 skewness (long low skew)
sk = R[COM].rolling(252, min_periods=240).skew()
report("H2 commodity skewness (long low skew)", daily_book(xs_monthly(sk, COM, 4, high_long=False), COM), "multi-day")
# H3 weekly XS reversal
fri = R.index.to_series().groupby(R.index.to_period("W")).max()
r5 = (1 + R.fillna(0.0)).rolling(5).apply(np.prod, raw=True) - 1
W = pd.DataFrame(np.nan, index=R.index, columns=ALL)
for d in fri:
    s = r5.loc[d].dropna()
    if len(s) < 12:
        continue
    w = pd.Series(0.0, index=ALL); iv = 1 / SD.loc[d]
    w[s.nsmallest(6).index] = iv[s.nsmallest(6).index]; w[s.nlargest(6).index] = -iv[s.nlargest(6).index]; W.loc[d] = w / w.abs().sum()
report("H3 weekly cross-sectional reversal (24)", daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), ALL), "multi-day")
# H4 bond multi-speed trend (Gen114 EWMAC on rates only)
t = {"__file__": str(ROOT / "scripts/gen114_futures.py")}
exec(open(ROOT / "scripts/gen114_futures.py").read().split("rows, PNL = [], {}")[0], t)
RATES = ["ZT", "ZF", "ZN", "ZB"]; p4, _ = t["book_daily"](t["TR"], RATES)
report("H4 bond multi-speed trend", p4, "multi-day")
# H5 curve trend: ZN vs ZT duration-neutral
v60 = R[["ZN", "ZT"]].rolling(60).std() * np.sqrt(252)
spread = (R.ZN / v60.ZN.shift(1) - R.ZT / v60.ZT.shift(1)).fillna(0.0)
sig = np.sign(spread.rolling(63).sum()); s = pd.Series(np.nan, index=R.index); s.loc[fri] = sig.loc[fri]; s = s.ffill().fillna(0.0)
W5 = pd.DataFrame({"ZN": s * 0.5 * 0.10 / v60.ZN, "ZT": -s * 0.5 * 0.10 / v60.ZT}).shift(1).fillna(0.0)
report("H5 yield-curve trend (ZN vs ZT)", daily_book(W5, ["ZN", "ZT"]), "multi-day")
pd.DataFrame(rows).to_csv(ROOT / "results/gen136.csv", index=False)
pd.DataFrame(PNL).to_parquet(ROOT / "results/gen136_daily.parquet")
