"""Gen119 (config/gen119_protocol.json): CFTC COT signals. Report date = Tuesday; usable from the following Monday (report + 6 days).
Writes results/gen119.csv."""
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
M2 = ROOT / "research_data/more2"
DIS = {"GC": "088691", "SI": "084691", "HG": "085692", "CL": "067651", "NG": "023651", "RB": "111659", "HO": "022651", "ZC": "002602",
       "ZS": "005602", "ZW": "001602", "LE": "057642", "HE": "054642"}
TFF = {"ES": "13874A", "NQ": "209742", "ZN": "043602", "ZB": "020601", "6E": "099741", "6J": "097741", "6B": "096742", "6A": "232741"}


def load(fname, codes, cols):
    d = pd.read_parquet(M2 / fname)
    d["code"] = d.CFTC_Contract_Market_Code.astype(str).str.strip()
    # the report date sits in different columns and formats across the yearly files: take the first one that parses
    rep = pd.Series(pd.NaT, index=d.index)
    for c in ("Report_Date_as_YYYY-MM-DD", "Report_Date_as_MM_DD_YYYY"):
        if c in d:
            rep = rep.fillna(pd.to_datetime(d[c].astype(str).str.strip().str[:10], format="mixed", errors="coerce"))
    if "As_of_Date_In_Form_YYMMDD" in d:
        rep = rep.fillna(pd.to_datetime(d["As_of_Date_In_Form_YYMMDD"].astype(str).str.strip().str.zfill(6), format="%y%m%d", errors="coerce"))
    d["rep"] = rep; d = d[["code", "rep", "Open_Interest_All"] + cols].dropna(subset=["rep"])
    out = {}
    for k, c in codes.items():
        x = d[d.code == c].drop_duplicates("rep").set_index("rep").sort_index()
        out[k] = x
    return out


def weekly_to_daily(sig, idx):
    """weekly signal by report date -> daily, effective from report + 6 days (Monday after the Friday release)."""
    s = sig.copy(); s.index = s.index + pd.Timedelta(days=6)
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def zscore(x, n, m):
    return (x - x.rolling(n, min_periods=m).mean()) / x.rolling(n, min_periods=m).std()


def contrarian_book(rec, members, net_cols, name, fit):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index(); vol = R.ewm(span=60, min_periods=40).std() * np.sqrt(252)
    W = pd.DataFrame(0.0, index=R.index, columns=members)
    for r in members:
        x = rec[r]; net = (x[net_cols[0]] - x[net_cols[1]]) / x["Open_Interest_All"]
        z = zscore(net, 156, 104); s = pd.Series(np.where(z > 1.5, -1.0, np.where(z < -1.5, 1.0, 0.0)), index=z.index)
        W[r] = weekly_to_daily(s, R.index).fillna(0.0) * (0.40 / vol[r]) / len(members)
    report(name, daily_book(W.shift(1).fillna(0.0).where(lambda w: np.isfinite(w), 0.0), members), fit)


dis = load("cot_disagg.parquet", DIS, ["M_Money_Positions_Long_All", "M_Money_Positions_Short_All", "Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All"])
tff = load("cot_tff.parquet", TFF, ["Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"])
contrarian_book(dis, list(DIS), ("M_Money_Positions_Long_All", "M_Money_Positions_Short_All"), "C1 managed money extremes, commodities (contrarian)", "multi-day")
contrarian_book(tff, list(TFF), ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"), "C2 leveraged funds extremes, financials (contrarian)", "multi-day")
# C3 hedging pressure
mem = list(DIS); R = pd.DataFrame({r: D[r].r for r in mem}).sort_index(); sd = R.ewm(span=35, min_periods=30).std()
hp = pd.DataFrame({r: weekly_to_daily((dis[r].Prod_Merc_Positions_Short_All - dis[r].Prod_Merc_Positions_Long_All) /
                                      (dis[r].Prod_Merc_Positions_Short_All + dis[r].Prod_Merc_Positions_Long_All), R.index) for r in mem})
W = pd.DataFrame(np.nan, index=R.index, columns=mem)
for d in R.index.to_series().groupby(R.index.to_period("M")).max():
    s = hp.loc[d].dropna()
    if len(s) < 8:
        continue
    w = pd.Series(0.0, index=mem); iv = 1 / sd.loc[d]
    w[s.nlargest(4).index] = iv[s.nlargest(4).index]; w[s.nsmallest(4).index] = -iv[s.nsmallest(4).index]; W.loc[d] = w / w.abs().sum()
report("C3 hedging pressure (Basu-Miffre)", daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), mem), "multi-day")
pd.DataFrame(rows).to_csv(ROOT / "results/gen119.csv", index=False)

# C4 CME bitcoin leveraged funds -> crypto books
g2 = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g2)
b = load("cot_tff.parquet", {"BTC": "133741"}, ["Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"])["BTC"]
z = zscore((b.Lev_Money_Positions_Long_All - b.Lev_Money_Positions_Short_All) / b.Open_Interest_All, 52, 40)
s = pd.Series(np.where(z > 1.5, -0.5, np.where(z < -1.5, 0.5, 0.0)), index=z.index)
days = g2["days"]; s.index = s.index + pd.Timedelta(days=5)          # row d = decided at the close of d (Sunday) -> held from Monday
w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]); w["BTC"] = s.reindex(s.index.union(days)).ffill().reindex(days).fillna(0.0)
print("C4 active days:", int((w.BTC != 0).sum()), flush=True)
g2["evaluate"]("C4 CME bitcoin leveraged funds (contrarian)", w)
pd.DataFrame(g2["rows"]).to_csv(ROOT / "results/gen119_crypto.csv", index=False)
