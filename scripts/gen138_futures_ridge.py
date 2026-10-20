"""Gen138 (config/gen138_protocol.json): walk-forward ridge across 24 CME futures. Writes results/gen138.csv, results/gen138_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
src = open(ROOT / "scripts/gen127_multi.py").read()
g = {"__file__": str(ROOT / "scripts/gen127_multi.py")}
exec(src[:src.index("# P1 IBS futures")], g)
D, daily_book, report, rows, PNL, daily_hl = (g[k] for k in ("D", "daily_book", "report", "rows", "PNL", "daily_hl"))
c = {"__file__": str(ROOT / "scripts/gen119_cot.py")}
cs = open(ROOT / "scripts/gen119_cot.py").read(); exec(cs[:cs.index("def contrarian_book")], c)
ROOTS = F.NONCRYPTO
R = pd.DataFrame({r: D[r].r for r in ROOTS}).sort_index(); R = R[R.index.weekday < 5]; idx = R.index
vol = R.rolling(60, min_periods=40).std()
cum = lambda h: (1 + R.fillna(0.0)).rolling(h).apply(np.prod, raw=True) - 1
feats = {f"r{h}": cum(h) / (vol * np.sqrt(h)) for h in (1, 5, 20, 60, 250)}
feats["carry"] = pd.DataFrame({r: (D[r].near_far - 1) / F.SPEC[r][3] for r in ROOTS}).reindex(idx) / (vol * np.sqrt(252))
H = {r: daily_hl(r) for r in ROOTS}
feats["ibs"] = pd.DataFrame({r: ((H[r].c - H[r].lo) / (H[r].hi - H[r].lo)).where(H[r].ids == 1) for r in ROOTS}).reindex(idx)
dis = c["load"]("cot_disagg.parquet", c["DIS"], ["M_Money_Positions_Long_All", "M_Money_Positions_Short_All"])
tff = c["load"]("cot_tff.parquet", c["TFF"], ["Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"])
cot = {}
for r, x in {**dis, **tff}.items():
    lo, sh_ = ("M_Money_Positions_Long_All", "M_Money_Positions_Short_All") if r in dis else ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All")
    net = (x[lo] - x[sh_]) / x.Open_Interest_All; z = c["zscore"](net, 156, 104)
    cot[r] = c["weekly_to_daily"](z, idx)
feats["cot"] = pd.DataFrame(cot).reindex(index=idx, columns=ROOTS)
last3 = idx.to_series().groupby(idx.to_period("M")).transform(lambda s: s.rank(ascending=False) <= 3).astype(float)
feats["monthend"] = pd.DataFrame({r: last3 for r in ROOTS})
fwd = ((1 + R.fillna(0.0))[::-1].rolling(5).apply(np.prod, raw=True)[::-1] - 1).shift(-1) / (vol * np.sqrt(5))
names = list(feats)
long = pd.concat({k: v.stack(future_stack=True) for k, v in feats.items()}, axis=1)
long["y"] = fwd.stack(future_stack=True); long.index.names = ["day", "root"]
long = long.dropna(subset=["r250", "r60", "r20", "r5", "r1"])
pred = pd.Series(np.nan, index=long.index)
months = pd.date_range("2013-01-01", "2026-09-01", freq="MS")
for m in months:
    tr = long[(long.index.get_level_values("day") < m - pd.Timedelta(days=7)) & long.y.notna()]   # targets fully known before m
    te = long[(long.index.get_level_values("day") >= m) & (long.index.get_level_values("day") < m + pd.offsets.MonthBegin(1))]
    if len(tr) < 5000 or not len(te):
        continue
    X = tr[names].fillna(0.0); mu, sd = X.mean(), X.std().replace(0, 1)
    mdl = Ridge(alpha=10.0).fit(((X - mu) / sd).clip(-5, 5), tr.y.clip(-5, 5))
    pred[te.index] = mdl.predict(((te[names].fillna(0.0) - mu) / sd).clip(-5, 5))
P = pred.unstack("root").reindex(index=idx, columns=ROOTS)
fri = idx.to_series().groupby(idx.to_period("W")).max()
xsd = P.stack().groupby(level=0).std().rolling(52 * 5, min_periods=100).mean()
W = pd.DataFrame(np.nan, index=idx, columns=ROOTS)
for d in fri:
    if d in P.index and np.isfinite(xsd.get(d, np.nan)) and P.loc[d].notna().any():
        W.loc[d] = (P.loc[d] / xsd[d]).clip(-2, 2) * 0.10 / (vol.loc[d] * np.sqrt(252)) / len(ROOTS)
W = W.ffill().fillna(0.0).shift(1).fillna(0.0)
report("Gen138 futures walk-forward ridge (24 markets)", daily_book(W, ROOTS).loc["2013-01-01":], "multi-day (weekly)")
mdl_all = Ridge(alpha=10.0).fit(((long[names].fillna(0.0) - long[names].fillna(0.0).mean()) / long[names].fillna(0.0).std()).clip(-5, 5), long.y.fillna(0.0).clip(-5, 5))
print("full-sample coefficients (descriptive):", dict(zip(names, np.round(mdl_all.coef_, 4))), flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen138.csv", index=False); pd.DataFrame(PNL).to_parquet(ROOT / "results/gen138_daily.parquet")
