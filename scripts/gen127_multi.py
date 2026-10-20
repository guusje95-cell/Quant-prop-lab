"""Gen127 (config/gen127_protocol.json): multi-sleeve futures/CFD round. Writes results/gen127.csv, results/gen127_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")
import futures_db as F
src = open(ROOT / "scripts/gen122_futures.py").read()
g = {"__file__": str(ROOT / "scripts/gen122_futures.py")}
exec(src[:src.index("# F1 / F2")] + src[src.index("# daily helpers"):src.index("# F3")], g)
D, daily_book, report, rows, PNL = (g[k] for k in ("D", "daily_book", "report", "rows", "PNL"))
import gen124_intraday as I
DUK = ROOT / "research_data/dukascopy"
CFD_SPL = (("2013-01-01", "2017-12-31"), ("2018-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30"))


def report_splits(name, p, splits, fit):
    p = p.sort_index(); k = tuple(round(I.sharpe(p, a, b), 3) for a, b in splits)
    r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3), "prop fit": fit,
         "active days": int((p != 0).sum())}
    rows.append(r); PNL[name] = p; print(r, flush=True)


def daily_hl(r):
    f = F.front(r); td = F.trade_date(f.index); gg = f.groupby(td)
    out = pd.DataFrame({"hi": gg.high.max(), "lo": gg.low.min(), "c": gg.close.last(), "roll": gg.roll.max(), "ids": gg.instrument_id.nunique()})
    return out[out.index.weekday < 5]


def ibs_weights(H, members, size=0.25):
    W = {}
    for r in members:
        h = H[r]; ibs = (h.c - h.lo) / (h.hi - h.lo); ok = (h.ids == 1) & (h.hi > h.lo)
        W[r] = pd.Series(np.where(ok & (ibs < 0.2), size, np.where(ok & (ibs > 0.8), -size, 0.0)), index=h.index)
    return pd.DataFrame(W)


# P1 IBS futures
EQ = ["ES", "NQ", "RTY", "YM"]; H = {r: daily_hl(r) for r in EQ}
W1 = ibs_weights(H, EQ).reindex(pd.DataFrame({r: D[r].r for r in EQ}).index).fillna(0.0).shift(1).fillna(0.0)
report("P1 IBS reversal, equity index futures", daily_book(W1, EQ), "1-day holds (overnight: MFFU/Tradeify; Topstep only in-session)")


def pair_book(a, b, la, lb, win, maxd, name, returns, cost_a, cost_b, splits=None, fit="multi-day"):
    """Mean reversion of log(la/lb) (adjusted price indices), z over `win` days; |z|>2 enter, |z|<0.5 or maxd days exit."""
    lr = np.log(la / lb); z = (lr - lr.rolling(win).mean()) / lr.rolling(win).std()
    va = returns[a].rolling(60).std() * np.sqrt(252); vb = returns[b].rolling(60).std() * np.sqrt(252)
    pos = pd.Series(0.0, index=z.index); cur, age = 0.0, 0
    for i, t in enumerate(z.index):
        zt = z.iloc[i]
        if cur != 0:
            age += 1
            if (np.isfinite(zt) and abs(zt) < 0.5) or age >= maxd:
                cur, age = 0.0, 0
        if cur == 0 and np.isfinite(zt) and abs(zt) > 2:
            cur, age = -np.sign(zt), 0                       # z high: short a / long b
        pos.iloc[i] = cur
    wa = (pos * 0.5 * 0.10 / va).shift(1).fillna(0.0); wb = (-pos * 0.5 * 0.10 / vb).shift(1).fillna(0.0)
    pnl = wa * returns[a].fillna(0.0) + wb * returns[b].fillna(0.0) - wa.diff().abs().fillna(0.0) * cost_a - wb.diff().abs().fillna(0.0) * cost_b
    if splits:
        report_splits(name, pnl, splits, fit)
    return pnl, wa, wb


def fut_pair(a, b, win, maxd, name):
    R = pd.DataFrame({a: D[a].r, b: D[b].r}).dropna(); px = (1 + R).cumprod()
    W = pd.DataFrame({a: 0.0, b: 0.0}, index=R.index)
    _, wa, wb = pair_book(a, b, px[a], px[b], win, maxd, None, R, 0, 0)
    W[a], W[b] = wa, wb
    report(name, daily_book(W, [a, b]), "multi-day")


fut_pair("GC", "SI", 120, 30, "P2 gold/silver ratio reversion")
fut_pair("RB", "CL", 60, 20, "P3 gasoline crack reversion")


# CFD daily from Dukascopy hourly (17:00 New York close)
def cfd_daily(sym):
    x = pd.read_parquet(DUK / f"{sym}_1h.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index(); x = x[x.close > 0]
    et = x.index.tz_localize("UTC").tz_convert("America/New_York")
    day = pd.DatetimeIndex(et.date) + pd.to_timedelta((et.hour >= 17).astype(int), unit="D")     # 17:00 ET roll
    gg = x.groupby(day)
    d = pd.DataFrame({"hi": gg.high.max(), "lo": gg.low.min(), "c": gg.close.last()})
    return d[d.index.weekday < 5].loc[:"2026-09-30"]


cb, cw = cfd_daily("BRENT"), cfd_daily("WTI")
RC = pd.DataFrame({"BRENT": cb.c.pct_change(), "WTI": cw.c.pct_change()}).dropna()
pair_book("BRENT", "WTI", cb.c.reindex(RC.index), cw.c.reindex(RC.index), 60, 20, "P4 Brent-WTI reversion (CFD)", RC, 4e-4, 4e-4, CFD_SPL, "multi-day (swap-free CFD)")

# P5 Baltussen rest-of-day -> last half hour (1-minute futures)
per = []
for r in ("ES", "NQ"):
    B = I.bars_futures(r); out = {}; prev = (np.nan, None)
    for day, gd in B.groupby(B.index.normalize()):
        if day.weekday() >= 5:
            continue
        p1530, i1 = I.last_before(gd, "15:30"); p16, i2 = I.last_before(gd, "16:00")
        if np.isfinite(prev[0]) and np.isfinite(p1530) and np.isfinite(p16) and prev[1] == i1 == i2:
            side = np.sign(p1530 / prev[0] - 1)
            if side:
                out[day] = side * (p16 / p1530 - 1) - 2 * F.cost_frac(r, p1530)
        prev = (p16, i2)
    per.append(pd.Series(out, dtype=float))
p5 = pd.concat(per, axis=1).fillna(0.0).mean(axis=1).reindex(pd.date_range("2018-01-01", "2026-09-30", freq="B")).fillna(0.0)
report_splits("P5 rest-of-day -> last half hour ES/NQ", p5, I.SPL, "in-session (Topstep/Lucid OK)")

# P7 IBS on CFDs
idx_cfd = {s: cfd_daily(s) for s in ("US500", "US100", "US30", "US2000")}
pnl7 = []
for s, h in idx_cfd.items():
    ibs = (h.c - h.lo) / (h.hi - h.lo); w = pd.Series(np.where(ibs < 0.2, 0.25, np.where(ibs > 0.8, -0.25, 0.0)), index=h.index).shift(1).fillna(0.0)
    rr = h.c.pct_change().fillna(0.0); pnl7.append(w * rr - w.diff().abs().fillna(0.0) * 1e-4)
report_splits("P7 IBS reversal, index CFDs", pd.concat(pnl7, axis=1).fillna(0.0).sum(axis=1), CFD_SPL, "1-day holds (swap-free CFD)")

# P8 Nasdaq-vs-S&P style momentum (weekly)
R = pd.DataFrame({"NQ": D["NQ"].r, "ES": D["ES"].r}).dropna(); px = (1 + R).cumprod(); vol = R.rolling(60).std() * np.sqrt(252)
mom = (px.NQ / px.NQ.shift(20)) / (px.ES / px.ES.shift(20)) - 1
fri = R.index.to_series().groupby(R.index.to_period("W")).max()
s = pd.Series(np.nan, index=R.index); s.loc[fri] = np.sign(mom.loc[fri]); s = s.ffill().fillna(0.0)
W8 = pd.DataFrame({"NQ": s * 0.5 * 0.10 / vol.NQ, "ES": -s * 0.5 * 0.10 / vol.ES}).shift(1).fillna(0.0)
report("P8 Nasdaq-vs-S&P style momentum", daily_book(W8, ["NQ", "ES"]), "multi-day")
pd.DataFrame(rows).to_csv(ROOT / "results/gen127.csv", index=False)
pd.DataFrame(PNL).to_parquet(ROOT / "results/gen127_daily.parquet")
print("done", flush=True)
