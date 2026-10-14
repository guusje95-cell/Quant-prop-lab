"""Gen49 (config/gen49_protocol.json): papers 5-6, rest-of-day momentum, multi-index noise-area, C* portfolio-vol overlay,
multi-strategy risk parity. Writes results/gen49_research.csv and results/gen49_sleeves.parquet."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, analysis as A, futures_curve as FC, propfirms as PF, scorecard as SC
from qpl.lab import strategies as S
from qpl.lab.strategies_papers import (CurveSlopeMomentum, OvernightIndex, IntradayMomentumGao, NoiseAreaMomentum,
                                       VolatilityManaged, CurveMomentum)
from qpl.data import loaders as L

rows = []; SRC = D.list_sources(); N_TRIALS = 260


def daily_of(b, st, p, cost, lev=1.0, fund=0.0, start=None, weekdays=True):
    sig = st.signal(b, p); cfg = EN.Config(cost_bps=cost, leverage=lev, funding_bps_day=fund)
    r = EN.run(b, EN.size(b, sig, cfg, getattr(st, "sizing", "engine")), cfg)
    d = EN.to_daily(r["bars"], b.freq)
    nz = (sig != 0).any(axis=1)
    t0 = sig.index[nz][0].floor("D") if nz.any() else d.index[0]
    if start is not None:
        t0 = max(t0, pd.Timestamp(start))
    d = d.loc[t0:]
    return d[d.index.dayofweek < 5] if weekdays else d


def report(tag, d, cost, split=None):
    x = d["net"]; ppy = D.periods_per_year(x.index, "1d"); Sm = A.summary(x, ppy)
    row = {"test": tag, "cost_bp": cost, "sharpe": Sm["Sharpe"], "cagr": Sm["CAGR"], "vol": Sm["Volatility"], "max_dd": Sm["Max drawdown"],
           "pos_months": Sm["Positive months"], "years": Sm["Years"], "from": x.index[0].date(), "to": x.index[-1].date(),
           "dsr": A.dsr(x, ppy, N_TRIALS)}
    if split:
        a, z = A.split_stats(x, ppy, pd.Timestamp(split)); row["sharpe_h1"] = a.get("Sharpe"); row["sharpe_h2"] = z.get("Sharpe")
    rows.append(row); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    return row


def m15(sym):
    x = L.raw_dukascopy(sym, "M15"); x.index = x.index.tz_localize(None)
    f = lambda k: x[[k]].rename(columns={k: sym})
    return D.Bars(sym, "15m", f("open"), f("high"), f("low"), f("close"), f("volume"), D.periods_per_year(x.index, "15m"))


passed = {}
# ---------------- G49a NS slope dynamics
cb = FC.bars().select(start="1999-06-01")
r = report("G49a curve slope spread (continuation)", daily_of(cb, CurveSlopeMomentum(), CurveSlopeMomentum().defaults(), 8.0, start="2000-01-01", weekdays=False), 8.0, "2012-01-01")
passed["G49a"] = r["sharpe"] >= 0.5 and r["sharpe_h1"] > 0 and r["sharpe_h2"] > 0

# ---------------- G49b overnight (3 modes) and G49c rest-of-day
idx = {s: m15(s) for s in ("US500", "US100", "US30")}
on = OvernightIndex()
for mode in ("hold overnight (paper)", "first half hour: fade overnight", "last half hour: follow overnight"):
    res = {}
    for s, b in idx.items():
        fund = 1.0 if mode.startswith("hold") else 0.0
        res[s] = report(f"G49b {mode} {s}", daily_of(b, on, {"mode": mode}, 1.0, fund=fund), 1.0, "2018-09-01")
    passed[f"G49b {mode}"] = (res["US500"]["sharpe"] >= 0.8 and res["US500"]["sharpe_h1"] > 0 and res["US500"]["sharpe_h2"] > 0
                              and res["US100"]["sharpe"] > 0 and res["US30"]["sharpe"] > 0)
g = IntradayMomentumGao()
res = {s: report(f"G49c rest-of-day momentum {s}", daily_of(idx[s], g, dict(g.defaults(), mode="rest of day (Baltussen et al. 2021)"), 1.0), 1.0, "2018-09-01")
       for s in ("US500", "US100")}
passed["G49c"] = res["US500"]["sharpe"] >= 0.8 and res["US100"]["sharpe"] > 0

# ---------------- G49d noise-area on 3 indices together
nb = idx["US500"]
for s in ("US100", "US30"):
    for k in ("open", "high", "low", "close", "volume"):
        setattr(nb, k, getattr(nb, k).join(getattr(idx[s], k), how="outer"))
nb.periods_per_year = D.periods_per_year(nb.close.index, "15m")
na_daily = daily_of(nb, NoiseAreaMomentum(), NoiseAreaMomentum().defaults(), 1.0)
r = report("G49d noise-area US500+US100+US30", na_daily, 1.0, "2018-09-01")
passed["G49d"] = r["sharpe"] >= 0.8 and r["sharpe_h1"] > 0 and r["sharpe_h2"] > 0

# ---------------- C* baseline and G49e portfolio-vol overlay
cr = SRC["Binance spot majors (daily, 2017+)"]()
cstar = SC.run(S.CStarTrend, cr, SC.SETUPS["C* trend + breakout (E2)"])["daily"]
base = report("C* baseline 2018-2026", cstar, 7.5)
x = cstar["net"]; m = x.index.to_period("M")
rv = (x ** 2).groupby(m).sum(); scale = (rv.expanding().mean() / rv).shift(1).clip(upper=2.0)
sc = pd.Series(scale.reindex(m).to_numpy(), index=x.index).fillna(1.0)
ov = cstar.mul(sc, axis=0)
r = report("G49e C* + portfolio vol-managed overlay (cap 2)", ov, 7.5)
passed["G49e"] = r["sharpe"] >= base["sharpe"] + 0.1 and r["max_dd"] >= base["max_dd"]

# ---------------- G49f multi-strategy risk parity
sleeves = {"C*": cstar}
na_us100 = daily_of(idx["US100"], NoiseAreaMomentum(), NoiseAreaMomentum().defaults(), 1.0)
sleeves["noise-area US100"] = na_us100
fut = SRC["Futures daily, 250 markets (pysystemtrade, to 2024-03)"]()
sleeves["vol-managed SP500"] = daily_of(fut.select(["SP500"], start="1990-01-01"), VolatilityManaged(), VolatilityManaged().defaults(), 1.0,
                                        start="1991-01-01")
sleeves["curve momentum"] = daily_of(FC.bars().select(start="1995-01-01"), CurveMomentum(), CurveMomentum().defaults(), 8.0, lev=0.5,
                                     start="2000-01-01", weekdays=False)
extra = {"G49a": ("curve slope", lambda: daily_of(cb, CurveSlopeMomentum(), CurveSlopeMomentum().defaults(), 8.0, start="2000-01-01", weekdays=False)),
         "G49d": ("noise-area 3 indices", lambda: na_daily)}
for k, (nm, fn) in extra.items():
    if passed.get(k):
        sleeves[nm] = fn()
print("passed:", passed, "sleeves:", list(sleeves), flush=True)
t0, t1 = pd.Timestamp("2018-09-01"), pd.Timestamp("2023-09-11")
cal = pd.date_range(t0, t1, freq="D")
R = {k: v.reindex(cal).fillna(0.0) for k, v in sleeves.items()}
net = pd.DataFrame({k: v["net"] for k, v in R.items()}); worst = pd.DataFrame({k: v["worst"] for k, v in R.items()})
best = pd.DataFrame({k: v["best"] for k, v in R.items()})
# full history for trailing vols (before the window too)
hist = pd.DataFrame({k: v["net"] for k, v in sleeves.items()}).reindex(pd.date_range("2017-09-01", t1, freq="D")).fillna(0.0)
vol = hist.rolling(365, min_periods=180).std() * np.sqrt(365)
mfirst = ~hist.index.to_period("M").duplicated()
iv = (1 / vol).shift(1)[mfirst].reindex(hist.index).ffill()          # monthly, using data up to the day before the rebalance
wraw = iv.div(iv.sum(axis=1), axis=0)
mix = (hist * wraw).sum(axis=1)
pv = mix.rolling(365, min_periods=180).std() * np.sqrt(365)
lev = (0.15 / pv).shift(1)[mfirst].reindex(hist.index).ffill().clip(upper=3.0)
W = wraw.mul(lev, axis=0).reindex(cal)
port = pd.DataFrame({"net": (net * W).sum(axis=1), "worst": (worst.clip(upper=0) * W).sum(axis=1), "best": (best.clip(lower=0) * W).sum(axis=1)})
port["gross"] = port["net"]; port["cost"] = 0.0; port["funding"] = 0.0
cw = cstar.reindex(cal).fillna(0.0)
c_same = report("C* alone, same window 2018-09..2023-09", cw, 7.5)
pr = report("G49f multi-strategy risk parity (15% vol)", port, 0.0)
passed["G49f"] = pr["sharpe"] >= c_same["sharpe"] + 0.2 and pr["max_dd"] >= c_same["max_dd"]
print("correlations of sleeves (daily):\n", net.corr().round(2).to_string())
print("average weights:\n", W.mean().round(3).to_string())
for nm, dd in (("C* alone", cw), ("multi-strategy", port)):
    for firm in ("Crypto Fund Trader 1-Phase $100k", "FTMO 2-Step $100k"):
        f = PF.PRESETS[firm]; a = PF.attempts(dd, f); p = PF.pipeline(dd, f, 5, 1, 1.0, 0.4, horizon_days=730)
        print(f"PROP {nm:15s} {firm:35s} pass {a['P_pass']:.0%} funded {p['P_funded']:.0%} net {p['net_mean']:8.0f} p50 {p['net_p50']:8.0f} P(profit) {p['P_profit']:.0%}", flush=True)
pd.concat({k: v["net"] for k, v in sleeves.items()}, axis=1).to_parquet(ROOT / "results/gen49_sleeves.parquet")
print("PASSED:", passed)
pd.DataFrame(rows).to_csv(ROOT / "results/gen49_research.csv", index=False)
