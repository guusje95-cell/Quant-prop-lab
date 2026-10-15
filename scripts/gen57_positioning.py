"""Gen57/Gen60 positioning and cross-sectional tests on Binance perps (pre-registered). T2 funding carry, T3 positioning (top-trader
L/S contrarian, OI x price), B3 CTREND-style weekly factor, B4/T4 liquidation-cascade reversal, B5 opening-bar taker flow,
T8 XS momentum with taker filter, B6 crowding overlay on C*. Returns include funding. Writes results/gen57_positioning.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T          # reuse report(), CSTAR, PER (runs nothing heavy on import? see guard below)
from qpl.lab import binance_pack as B

C = B.coins(); COST = 5 / 1e4
P = B.panel("close", "1D", C)                                    # close at 00:00 of day d+1, labelled d
R = P.pct_change(fill_method=None)                               # return of day d
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60


def ls_from_signal(sig, hold=1, frac=1 / 3, valid=None):
    """long top third / short bottom third of sig (decided at the close of d, held over d+1), equal weight, gross 2."""
    v = sig.notna() & listed if valid is None else valid & sig.notna() & listed
    rk = sig.where(v).rank(axis=1, pct=True); n = v.sum(axis=1)
    w = (rk > 1 - frac).astype(float).div((rk > 1 - frac).sum(axis=1), axis=0) - (rk <= frac).astype(float).div((rk <= frac).sum(axis=1), axis=0)
    w = w.where(n >= 6, 0.0).fillna(0.0)
    if hold > 1:
        keep = pd.Series(np.arange(len(w)) % hold == 0, index=w.index)
        w = w.where(keep, np.nan).ffill().fillna(0.0)
    held = w.shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * COST


rep = T.report
# T2 funding carry: long low funding, short high funding
for look in (1, 3, 7):
    fs = F.groupby(level=0).sum().reindex(P.index).rolling(look).mean()
    for hold in (1, 7):
        rep(f"T2 funding carry XS: long low / short high {look}d avg funding, hold {hold}d", ls_from_signal(-fs, hold))

# T3 positioning
M = {c: B.metrics(c) for c in C}
top = pd.DataFrame({c: M[c]["sum_toptrader_long_short_ratio"].resample("1D").last() for c in C}).reindex(P.index)
oi = pd.DataFrame({c: M[c]["sum_open_interest_value"].resample("1D").last() for c in C}).reindex(P.index)
z = (top - top.rolling(30).mean()) / top.rolling(30).std()
for hold in (1, 7):
    rep(f"T3a contrarian top-trader L/S z-score (30d), hold {hold}d", ls_from_signal(-z, hold))
doi = oi.pct_change(fill_method=None)
zz = lambda x: (x - x.rolling(30).mean()) / x.rolling(30).std()
s_oixp = -(zz(doi) * zz(R))
for hold in (1, 7):
    rep(f"T3b contrarian OI-change x price-change, hold {hold}d", ls_from_signal(s_oixp, hold))

# T8 XS momentum with taker-flow filter (momentum only where taker buy share agrees)
tq = B.panel("taker_buy_quote_volume", "1D", C); qv = B.panel("quote_volume", "1D", C)
share7 = (tq.rolling(7).sum() / qv.rolling(7).sum())
mom = P / P.shift(14) - 1
rep("T8 XS 14d momentum, taker-flow agreeing only, hold 7d", ls_from_signal(mom.where(np.sign(mom) == np.sign(share7 - 0.5)), 7))

# B3 CTREND-style: weekly, ridge-free simple version (pre-registered variant: equal-weight tercile of an expanding OLS forecast)
from sklearn.linear_model import ElasticNetCV
feats = {}
for n in (5, 20, 60, 120):
    feats[f"p{n}"] = P / P.rolling(n).mean() - 1
    feats[f"v{n}"] = qv / qv.rolling(n).mean() - 1
mon = P.index[P.index.dayofweek == 6]                           # Sunday close -> Monday 00:00 decision
fwd = (P.shift(-7) / P - 1)
X = pd.concat({k: v.loc[mon].stack() for k, v in feats.items()}, axis=1)
y = fwd.loc[mon].stack().reindex(X.index)
xs = X.groupby(level=0).rank(pct=True) - 0.5; ys = y.groupby(level=0).rank(pct=True) - 0.5
ok = xs.notna().all(axis=1) & ys.notna()
train = ok & (xs.index.get_level_values(0) <= "2022-05-31")
model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], cv=5).fit(xs[train], ys[train])
pred = pd.Series(model.predict(xs[ok]), index=xs[ok].index).unstack()
sig = pred.reindex(P.index).ffill(limit=6)
r_ct = ls_from_signal(sig, 1)
rep("B3 CTREND-style weekly elastic-net (frozen on data to 2022-05), tercile L/S", r_ct.loc["2022-06-01":], "holdout starts 2022-06")

# B4/T4 liquidation-cascade reversal (hourly, OI from 2021-12)
def cascade(coin, hold=12, k=3.0):
    h = B.k5(coin); c = h.close.resample("1h").last(); lo = h.low.resample("1h").min(); hi = h.high.resample("1h").max(); v = h.quote_volume.resample("1h").sum()
    o = B.metrics(coin)["sum_open_interest_value"].resample("1h").last().reindex(c.index)
    r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
    atr = (hi - lo).rolling(14).mean()
    long_ev = (r < -k * sd) & (doi < -0.05) & (v > vq)
    short_ev = (r > k * sd) & (doi < -0.05) & (v > vq)
    pnl = pd.Series(0.0, index=c.index); cv = c.to_numpy(); n = len(cv)
    for ev, side in ((long_ev, 1), (short_ev, -1)):
        for t in np.flatnonzero(ev.to_numpy()):
            if t + 1 >= n:
                continue
            entry = cv[t]; stop = (lo.iloc[t] - atr.iloc[t]) if side > 0 else (hi.iloc[t] + atr.iloc[t])
            ex = None
            for j in range(t + 1, min(t + 1 + hold, n)):
                if (side > 0 and lo.iloc[j] <= stop) or (side < 0 and hi.iloc[j] >= stop):
                    ex = (j, stop); break
            if ex is None:
                j = min(t + hold, n - 1); ex = (j, cv[j])
            pnl.iloc[ex[0]] += 0.2 * (side * (ex[1] / entry - 1) - 2 * COST)
    return pnl.groupby(pnl.index.floor("D")).sum()


for hold in (12, 4, 24):
    cas = pd.concat([cascade(c, hold) for c in C], axis=1).sum(axis=1)
    rep(f"B4 liquidation-cascade reversal, 20 coins, hold {hold}h (0.2 notional per event)", cas.loc["2021-12-01":], "OI data from 2021-12")

# B5 opening-bar taker flow (first 5-min bar of the UTC day; paper uses the first minute), hold 8h, from 2024-11
def opening(coin):
    k = B.k5(coin); days = k.index.floor("D").unique()
    b = k.reindex(days)
    sgn = np.sign(2 * b.taker_buy_volume - b.volume)
    p0 = k.close.reindex(days); p1 = k.close.reindex(days + pd.Timedelta(hours=8) - pd.Timedelta(minutes=5))
    return pd.Series(sgn.to_numpy() * (p1.to_numpy() / p0.to_numpy() - 1) - 2 * COST, index=days).dropna()


b5 = pd.concat([opening(c) for c in ("BTC", "ETH", "SOL", "XRP", "DOGE", "ADA")], axis=1).mean(axis=1)
rep("B5 opening-bar taker imbalance, 6 coins, hold 8h (from 2024-11)", b5.loc["2024-11-01":], "5-min bar instead of 1-min")

out = pd.DataFrame(T.ROWS[len(T.ROWS) - sum(1 for r in T.ROWS if r['strategy'][:2] in ('T2', 'T3', 'T8', 'B3', 'B4', 'B5')):])
out.to_csv(ROOT / "results/gen57_positioning.csv", index=False)
