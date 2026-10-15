"""Gen63 (config/gen63_protocol.json): more crypto-only ideas. Writes results/gen63_crypto.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import gen57_cascade_hourly as CH
from qpl.lab import binance_pack as B, engine as EN, strategies as S
from qpl.lab.data import Bars

C = B.coins(); COST = 5 / 1e4
O, Hh, L, P, V = (B.panel(f, "1D", C).loc[:"2026-09-30"] for f in ("open", "high", "low", "close", "quote_volume"))
R = P.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60
ROWS = T.ROWS


def pnl_w(w, cost=COST):
    held = w.reindex(P.index).fillna(0.0).shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * cost


def rep(name, x, note=""):
    T.report(name, x, note); ROWS[-1]["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)


# ---------------- I1: C* on 20 vs 10 coins (perp bars, funding)
def cstar_perp(coins):
    b = Bars("binance perps", "1d", O[coins], Hh[coins], L[coins], P[coins], V[coins], 365.0)
    cs = S.CStarTrend(); sig = cs.signal(b, {**cs.defaults(), "btc_leads": True})
    cfg = EN.Config(cost_bps=7.5, vol_lookback_days=30, leverage=1.0)
    w = EN.size(b, sig, cfg)
    raw = pnl_w(w, 7.5 / 1e4)
    k = 0.15 / (raw.loc["2020-03-01":"2022-12-31"].std() * np.sqrt(365))
    return pnl_w(w * k, 7.5 / 1e4)


c10 = cstar_perp(B.MAJ10); c20 = cstar_perp(C)
rep("I1 baseline: C* 10 coins (perp bars, funding)", c10); rep("I1 C* on 20 coins", c20)

# ---------------- cascade events (shared)
def events(k=3.0, H=12):
    out = []
    for coin in C:
        d = CH.hourly(coin).loc[:"2026-09-30 23:00"]; c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
        r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
        atr = (hi - lo).rolling(14).mean(); ev = (r < -k * sd) & (doi < -0.05) & (v > vq)
        cv, lov, atv = c.to_numpy(), lo.to_numpy(), atr.to_numpy(); n = len(cv)
        for t in np.flatnonzero(ev.to_numpy()):
            if t + 1 >= n:
                continue
            stop = lov[t] - atv[t]; ex = None
            for j in range(t + 1, min(t + 1 + H, n)):
                if lov[j] <= stop:
                    ex = (j, stop); break
            if ex is None:
                ex = (min(t + H, n - 1), cv[min(t + H, n - 1)])
            out.append((c.index[t], coin, c.index[ex[0]], ex[1] / cv[t] - 1 - 2 * COST, (cv[t] - stop) / cv[t]))
    return sorted(out, key=lambda x: (x[0], x[1]))


def cap_book(evs, sizer, K=3):
    open_ex, pnl = [], {}
    for t0, coin, t1, ret, sd in evs:
        open_ex = [e for e in open_ex if e > t0]
        if len(open_ex) >= K:
            continue
        open_ex.append(t1); d = t1.floor("D"); pnl[d] = pnl.get(d, 0.0) + sizer(sd) * ret
    return pd.Series(pnl).sort_index().reindex(pd.date_range("2021-12-01", "2026-09-30")).fillna(0.0)


ev = events()
rep("I2 baseline: cascade fixed 0.2 notional, max 3", cap_book(ev, lambda sd: 0.2))
rep("I2 cascade risk-based sizing (0.4% risk at stop, cap 0.5)", cap_book(ev, lambda sd: min(0.5, 0.004 / max(sd, 1e-4))))

# ---------------- I3 short-squeeze continuation
fund3 = F.groupby(level=0).mean().reindex(P.index).rolling(1).mean()          # daily mean of the 3 settlements
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].resample("1D").last() for c in C}).reindex(P.index)
sig3 = (fund3 < -0.0001) & (P / P.shift(3) - 1 > 0) & (oi / oi.shift(3) - 1 > 0) & listed
w3 = pd.DataFrame(0.0, index=P.index, columns=C)
active = {}
for d in P.index:
    active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
    for c in sig3.columns[sig3.loc[d].fillna(False).to_numpy()]:
        if c not in active and len(active) < 5:
            active[c] = 3
    for c in active:
        w3.at[d, c] = 0.1
rep("I3 short-squeeze continuation", pnl_w(w3), "OI from 2021-12")

# ---------------- I4 premium carry with trend alignment
prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(7).mean()
rk = prem.where(listed).rank(axis=1, pct=True); lo_, hi_ = rk <= 1 / 3, rk > 2 / 3
ma50 = P.rolling(50).mean(); up = ma50 > ma50.shift(10); dn = ma50 < ma50.shift(10)
base_w = lo_.astype(float).div(lo_.sum(axis=1), axis=0) - hi_.astype(float).div(hi_.sum(axis=1), axis=0)
aligned = base_w.where(((base_w > 0) & up) | ((base_w < 0) & dn), 0.0)
weekly = pd.Series(np.arange(len(P)) % 7 == 0, index=P.index)
for nm, w in (("I4 baseline: G4 premium carry", base_w), ("I4 premium carry, trend-aligned legs", aligned)):
    rep(nm, pnl_w(w.fillna(0.0).where(weekly, np.nan).ffill().fillna(0.0)))

# ---------------- I5 daily dip-buy in uptrends
sd30 = R.rolling(30).std().shift(1); ma100 = P.rolling(100).mean()
sig5 = (R < -2.5 * sd30) & (P > ma100) & listed
w5 = pd.DataFrame(0.0, index=P.index, columns=C); active = {}
for d in P.index:
    active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
    for c in sig5.columns[sig5.loc[d].fillna(False).to_numpy()]:
        if c not in active and len(active) < 3:
            active[c] = 3
    for c in active:
        w5.at[d, c] = 0.2
rep("I5 daily dip-buy in uptrends", pnl_w(w5))

# ---------------- I6 4-hour breakout trend sleeve
def trend4h(coin, n_in=20, n_out=10, cost=5):
    k = B.k5(coin); c = k.close.resample("4h").last().loc[:"2026-09-30 23:00"]; h = k.high.resample("4h").max(); l = k.low.resample("4h").min()
    hi_in, lo_in = h.rolling(n_in).max().shift(1), l.rolling(n_in).min().shift(1)
    hi_out, lo_out = h.rolling(n_out).max().shift(1), l.rolling(n_out).min().shift(1)
    pos = np.zeros(len(c)); p = 0
    for i in range(len(c)):
        if p == 0:
            p = 1 if c.iloc[i] > hi_in.iloc[i] else (-1 if c.iloc[i] < lo_in.iloc[i] else 0)
        elif p == 1 and c.iloc[i] < lo_out.iloc[i]:
            p = 0
        elif p == -1 and c.iloc[i] > hi_out.iloc[i]:
            p = 0
        pos[i] = p
    pos = pd.Series(pos, index=c.index)
    r = c.pct_change().fillna(0)
    vol = r.rolling(6 * 30).std().shift(1) * np.sqrt(6 * 365)
    lev = (0.10 / vol).clip(upper=2.0).fillna(0)
    held = (pos * lev).shift(1).fillna(0)
    f = B.funding(coin).reindex(c.index).fillna(0.0)                         # settlements fall on 4h boundaries
    pnl = held * r - held * f.shift(-1).fillna(0) - held.diff().abs().fillna(0) * cost / 1e4
    return pnl.groupby(pnl.index.floor("D")).sum()


i6 = pd.concat([trend4h(c) for c in ("BTC", "ETH", "SOL")], axis=1).fillna(0).mean(axis=1)
rep("I6 4-hour breakout trend BTC/ETH/SOL (long-short)", i6)
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen63_crypto.csv", index=False)
