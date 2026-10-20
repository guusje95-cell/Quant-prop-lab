"""Gen115 U1-U8 (config/gen115_protocol.json): futures-native ideas on Databento CME hourly. Writes results/gen115.csv and
results/gen115_daily.parquet (daily P&L per idea, for the futures book)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F

rows, PNL = [], {}


def have(*rs):
    return all((F.DB / f"{r}_1h.parquet").exists() for r in rs)


def by_date(sig, t, m):
    return t.date[m].map(sig).fillna(0.0).to_numpy()


def run_hourly(name, P):
    tot = []
    for r, p in P.items():
        f = F.front(r); p = p.reindex(f.index).fillna(0.0); c = F.cost_frac(r, f.close)
        tot.append(p * f.r - p.diff().abs().fillna(p.abs()) * c - p.abs() * f.roll * 2 * c)
    pnl = pd.concat(tot, axis=1).fillna(0.0).sum(axis=1); pnl = pnl.groupby(pnl.index.floor("D")).sum()
    k = F.splits(pnl); r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": F.passes(k),
                             "trading days": int((pnl != 0).sum())}
    rows.append(r); PNL[name] = pnl; print(r, flush=True)


def ft(r):
    f = F.front(r); return f, F.ny(f.index), (1 + f.r).cumprod()


# U1 EIA crude day
if have("CL"):
    f, t, px = ft("CL"); m10 = (t.h == 10) & (t.wd == 2)
    s = np.sign(f.r[m10]).groupby(t.date[m10]).first()
    m = t.h.between(11, 14) & (t.wd == 2); P = pd.Series(0.0, index=f.index); P[m] = by_date(s, t, m)
    run_hourly("U1 EIA crude day", {"CL": P})
# U2 opening-hour range breakout
if have("ES", "NQ", "GC", "CL"):
    P = {}
    for r in ("ES", "NQ", "GC", "CL"):
        f, t, _ = ft(r); p = pd.Series(0.0, index=f.index)
        for d, g in f.groupby(t.date):
            tt = t.loc[g.index]; rb = g[tt.h == 9]
            if rb.empty:
                continue
            hi, lo = rb.high.iloc[0], rb.low.iloc[0]
            cand = g[(tt.h >= 10) & (tt.h <= 14)]
            for ts, row in cand.iterrows():
                side = 1.0 if row.close > hi else (-1.0 if row.close < lo else 0.0)
                if side:
                    hold = g.index[(g.index > ts) & (tt.h <= 15).to_numpy()]
                    p[hold] = 0.5 * side; break
        P[r] = p
    run_hourly("U2 opening-hour range breakout", P)
# U3 overnight-intraday reversal
if have("ES", "NQ"):
    P = {}
    for r in ("ES", "NQ"):
        f, t, px = ft(r)
        c8 = px[t.h == 8].groupby(t.date[t.h == 8]).last(); c17 = px[t.h == 16].groupby(t.date[t.h == 16]).last()      # CME halts 17-18 ET: last price before the reopen
        night = np.sign(c8 / c17.shift(1, freq="D").reindex(c8.index) - 1).dropna()
        m = t.h.between(10, 15); p = pd.Series(0.0, index=f.index); p[m] = -0.5 * by_date(night, t, m); P[r] = p
    run_hourly("U3 overnight-intraday reversal", P)
# U4 bond-equity lead
if have("ES", "ZN"):
    z, tz_, _ = ft("ZN"); s = np.sign(z.r[tz_.h == 9]).groupby(tz_.date[tz_.h == 9]).first()
    f, t, _ = ft("ES"); m = t.h.between(10, 15); p = pd.Series(0.0, index=f.index); p[m] = -by_date(s, t, m)
    run_hourly("U4 bond-equity lead", {"ES": p})
# U5 cross-sectional momentum (monthly 12-1), U6 commodity curve carry
roots = [r for r in F.NONCRYPTO if have(r)]
D = {r: F.daily(r) for r in roots}; R = pd.DataFrame({r: D[r].r for r in roots}).sort_index()
SD = R.ewm(span=35, min_periods=30).std(); COST = pd.DataFrame({r: D[r].cost for r in roots}).reindex(R.index).ffill()
ROLL = pd.DataFrame({r: D[r].roll for r in roots}).reindex(R.index).fillna(0)


def monthly_xs(score, members, n_side, name):
    me = R.index.to_series().groupby(R.index.to_period("M")).max()
    W = pd.DataFrame(np.nan, index=R.index, columns=members)
    for d in me:
        s = score.loc[d, members].dropna()
        if len(s) < 2 * n_side:
            continue
        w = pd.Series(0.0, index=members); iv = 1 / SD.loc[d, members]
        w[s.nlargest(n_side).index] = iv[s.nlargest(n_side).index]; w[s.nsmallest(n_side).index] = -iv[s.nsmallest(n_side).index]
        W.loc[d] = w / w.abs().sum()
    held = W.ffill().fillna(0.0).shift(1).fillna(0.0)
    turn = held.diff().abs().fillna(held.abs()) + 2 * held.abs() * ROLL[members]
    pnl = (held * R[members].fillna(0.0)).sum(axis=1) - (turn * COST[members]).sum(axis=1)
    k = F.splits(pnl); r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": F.passes(k)}
    rows.append(r); PNL[name] = pnl; print(r, flush=True)


px = (1 + R.fillna(0.0)).cumprod()
monthly_xs(px.shift(21) / px.shift(252) - 1, roots, 6, "U5 cross-sectional momentum 12-1")
comm = [r for r in ("GC", "SI", "HG", "CL", "NG", "RB", "HO", "ZC", "ZS", "ZW", "LE", "HE") if r in roots]
carry = pd.DataFrame({r: (D[r].near_far - 1) / F.SPEC[r][3] for r in comm}).reindex(R.index)
monthly_xs(carry, comm, 4, "U6 commodity curve carry")
# U7 FX month-end fix
if have("ES", "6E", "6J", "6B", "6A"):
    e, te, epx = ft("ES")
    c9 = epx[te.h == 9].groupby(te.date[te.h == 9]).last()
    days = c9.index; last = days[days.to_series().groupby(days.to_period("M")).transform("max") == days]
    mclose = epx.groupby(te.date).last(); mclose = mclose.groupby(mclose.index.to_period("M")).last()
    sgn = pd.Series({d: np.sign(c9[d] / mclose.get(d.to_period("M") - 1, np.nan) - 1) for d in last}).dropna()
    P = {}
    for r in ("6E", "6J", "6B", "6A"):                       # quoted USD per foreign unit: selling USD = long
        f, t, _ = ft(r); m = t.h == 10; p = pd.Series(0.0, index=f.index); p[m] = 0.25 * by_date(sgn, t, m); P[r] = p
    run_hourly("U7 FX month-end fix", P)
# U8 gold Asia-session drift
if have("GC"):
    f, t, _ = ft("GC"); m = (t.h >= 18) | (t.h <= 1)
    run_hourly("U8 gold Asia-session drift", {"GC": pd.Series(np.where(m, 1.0, 0.0), index=f.index)})
pd.DataFrame(rows).to_csv(ROOT / "results/gen115.csv", index=False)
pd.DataFrame(PNL).to_parquet(ROOT / "results/gen115_daily.parquet")
