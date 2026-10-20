"""Gen122 (config/gen122_protocol.json): futures round 2. Writes results/gen122.csv and results/gen122_daily.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F

v6 = pd.read_parquet(ROOT / "results/cache_v6_final.parquet")["portfolio"]; v6d = v6.groupby(v6.index.floor("D")).sum()
rows, PNL = [], {}


def report(name, pnl, fit):
    pnl = pnl.sort_index(); k = F.splits(pnl)
    c = pd.concat([pnl, v6d], axis=1).loc["2022":"2026-09-30"].dropna(); c = c[c.index.weekday < 5]
    r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": F.passes(k), "corr v6 2022-26": round(float(c.corr().iloc[0, 1]), 3),
         "active days": int((pnl != 0).sum()), "prop fit": fit}
    rows.append(r); PNL[name] = pnl; print(r, flush=True)


def hourly_pnl(P):
    tot = []
    for r, p in P.items():
        f = F.front(r); p = p.reindex(f.index).fillna(0.0); c = F.cost_frac(r, f.close)
        tot.append(p * f.r - p.diff().abs().fillna(p.abs()) * c - p.abs() * f.roll * 2 * c)
    x = pd.concat(tot, axis=1).fillna(0.0).sum(axis=1); return x.groupby(x.index.floor("D")).sum()


# F1 / F2
P1, P2 = {}, {}
for r in ("ES", "NQ"):
    f = F.front(r); t = F.ny(f.index); px = (1 + f.r).cumprod()
    m = t.h.isin([2, 3])
    P1[r] = pd.Series(np.where(m, 0.5, 0.0), index=f.index)
    c15 = px[t.h == 15].groupby(t.date[t.h == 15]).last(); c8 = px[t.h == 8].groupby(t.date[t.h == 8]).last()
    rth = (c15 / c8.reindex(c15.index) - 1).dropna()
    prev = rth.reindex(pd.date_range(rth.index.min(), t.date.max())).ffill().shift(1)    # last completed RTH before date D
    down = t.date[m].map(prev).lt(0).to_numpy()
    p = pd.Series(0.0, index=f.index); p[m] = np.where(down, 0.5, 0.0); P2[r] = p
report("F1 European-open overnight drift ES/NQ", hourly_pnl(P1), "in-session (Topstep/Lucid OK)")
report("F2 F1 after a down day", hourly_pnl(P2), "in-session (Topstep/Lucid OK)")

# daily helpers
D = {r: F.daily(r) for r in F.NONCRYPTO}


def daily_book(W, members):
    R = pd.DataFrame({r: D[r].r for r in members}).sort_index()
    COST = pd.DataFrame({r: D[r].cost for r in members}).reindex(R.index).ffill(); ROLL = pd.DataFrame({r: D[r].roll for r in members}).reindex(R.index).fillna(0)
    held = W.reindex(R.index).fillna(0.0)
    turn = held.diff().abs().fillna(held.abs()) + 2 * held.abs() * ROLL
    return (held * R.fillna(0.0)).sum(axis=1) - (turn * COST).sum(axis=1)


# F3 month-end Treasuries
B3 = ["ZN", "ZB", "ZF"]; R3 = pd.DataFrame({r: D[r].r for r in B3}).sort_index(); SD3 = R3.ewm(span=35, min_periods=30).std()
days = R3.index; W3 = pd.DataFrame(0.0, index=days, columns=B3)
for _, g in days.to_series().groupby(days.to_period("M")):
    if len(g) < 5:
        continue
    hold = g.index[-3:]                                          # the last 3 trading days are held (entered at the close 4 days before the last)
    iv = 1 / SD3.loc[g.index[-4]]; W3.loc[hold] = (iv / iv.sum() * 3 * 0.003 / SD3.loc[g.index[-4]].mean()).to_numpy() if np.isfinite(iv).all() else 0.0
report("F3 month-end Treasury demand", daily_book(W3, B3), "multi-day (MFFU/Tradeify); in-session variant would pay 2 extra round trips")

# F4 FX carry cross-section
FX = ["6E", "6J", "6B", "6A", "6C", "6S"]; RF = pd.DataFrame({r: D[r].r for r in FX}).sort_index(); SDF = RF.ewm(span=35, min_periods=30).std()
carry = pd.DataFrame({r: (D[r].near_far - 1) / 0.25 for r in FX}).reindex(RF.index)
W4 = pd.DataFrame(np.nan, index=RF.index, columns=FX)
for d in RF.index.to_series().groupby(RF.index.to_period("M")).max():
    s = carry.loc[d].dropna()
    if len(s) < 4:
        continue
    w = pd.Series(0.0, index=FX); iv = 1 / SDF.loc[d]
    w[s.nlargest(2).index] = iv[s.nlargest(2).index]; w[s.nsmallest(2).index] = -iv[s.nsmallest(2).index]
    W4.loc[d] = w / w.abs().sum()
report("F4 FX carry cross-section", daily_book(W4.ffill().fillna(0.0).shift(1).fillna(0.0), FX), "multi-day (MFFU/Tradeify)")

# F5 volatility-managed ES/NQ
E = ["ES", "NQ"]; RE = pd.DataFrame({r: D[r].r for r in E}).sort_index()
rv = RE.rolling(20).std() * np.sqrt(252)
W5 = (0.5 * (0.15 / rv).clip(upper=2.0)).shift(1).fillna(0.0)
report("F5 volatility-managed equity ES/NQ (beta)", daily_book(W5, E), "multi-day (MFFU/Tradeify); equity beta")

pd.DataFrame(rows).to_csv(ROOT / "results/gen122.csv", index=False)
pd.DataFrame(PNL).to_parquet(ROOT / "results/gen122_daily.parquet")
