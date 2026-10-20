"""Gen135 (config/gen135_protocol.json): nested out-of-sample futures book. Writes results/gen135.json, results/gen135_book.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
R = ROOT / "results"
pool = {}
t = pd.read_parquet(R / "gen114_futures_daily.parquet")
for k in ("T1 trend+carry multi-day (24 roots)", "T2 intraday momentum (last hour)", "T3 overnight drift ES/NQ"):
    pool[k] = t[k]
for f in ("gen115_daily", "gen122_daily", "gen123_daily"):
    d = pd.read_parquet(R / f"{f}.parquet"); pool.update({c: d[c] for c in d.columns})
d = pd.read_parquet(R / "gen127_daily.parquet")
for c in d.columns:
    if c.split()[0] in ("P1", "P2", "P3", "P8"):
        pool[c] = d[c]
pool["R1 Goldman roll"] = pd.read_parquet(R / "gen129_daily.parquet").iloc[:, 0]
a = pd.read_parquet(R / "gen130_daily.parquet"); pool["A3 auction round trip"] = a[[c for c in a.columns if c.startswith("A3")][0]]
pool["F1 post-FOMC drift"] = pd.read_parquet(R / "gen131_fomc_daily.parquet").iloc[:, 0]
pool["K3 pension rebalancing"] = pd.read_parquet(R / "gen125_daily.parquet")["K3 month-end pension rebalancing (ES)"]
P = pd.DataFrame(pool).sort_index(); P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
sel, table = [], {}
for c in P.columns:
    dev, test = F.sharpe(P[c], "2010-06-01", "2017-12-31"), F.sharpe(P[c], "2018-01-01", "2022-12-31")
    table[c] = (round(dev, 2), round(test, 2))
    if dev > 0 and test > 0.3:
        sel.append(c)
print("selected on 2010-2022 only:", sel, flush=True)
S = P[sel]; W = pd.DataFrame(np.nan, index=S.index, columns=sel)
for m in S.index[~S.index.to_period("M").duplicated()]:
    hist = S.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
    if len(hist) < 120:
        continue
    iv = 1 / hist.std().replace(0, np.nan); W.loc[m] = (iv / iv.sum()).fillna(0.0)
W = W.ffill()
raw = (S * W).sum(axis=1).where(W.notna().any(axis=1))
lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
book = (raw * lvl).dropna()
v6 = pd.read_parquet(R / "cache_v6_final.parquet")["portfolio"]; v6d = v6.groupby(v6.index.floor("D")).sum()
bf = pd.read_parquet(R / "cache_bf_final.parquet")["portfolio"]; bfd = bf.groupby(bf.index.floor("D")).sum()
cor = lambda x: round(float(pd.concat([book, x], axis=1).dropna().loc["2023":].corr().iloc[0, 1]), 3)
eq = (1 + book.loc["2023":]).cumprod()
out = {"pool (DEV 2010-17, TEST 2018-22)": table, "selected": sel,
       "book DEV / TEST / HOLD": [round(F.sharpe(book, a, b), 3) for a, b in F.SPLITS],
       "judgement: HOLD 2023-26": round(F.sharpe(book, "2023-01-01", "2026-09-30"), 3),
       "HOLD ann return at 10% vol": round(float(book.loc["2023":].mean() * 252), 4), "HOLD max DD": round(float((eq / eq.cummax() - 1).min()), 3),
       "corr v6 / bf 2023-26": [cor(v6d), cor(bfd)]}
out["pass"] = bool(out["judgement: HOLD 2023-26"] >= 0.5)
print(json.dumps(out, indent=1)); json.dump(out, open(R / "gen135.json", "w"), indent=1)
book.to_frame("book").to_parquet(R / "gen135_book.parquet")
