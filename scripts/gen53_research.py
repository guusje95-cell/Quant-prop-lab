"""Gen53 (config/gen53_protocol.json). Writes results/gen53_research.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import data as D, engine as EN, propfirms as PF, strategies as S, analysis as A

DEV, TEST = G.DEV, G.TEST
rows = []


def summ(tag, x, extra=None):
    x = x.loc[DEV[0]:]
    def sh(y): return float(y.mean() / y.std() * np.sqrt(365)) if y.std() > 0 else np.nan
    eq = (1 + x).cumprod(); mdd = float((eq / eq.cummax() - 1).min())
    r = {"test": tag, "sharpe": sh(x), "sharpe_dev": sh(x.loc[DEV[0]:DEV[1]]), "sharpe_test": sh(x.loc[TEST[0]:]),
         "cagr": float(eq.iloc[-1] ** (365 / len(x)) - 1), "max_dd": mdd, "worst_day": float(x.min()), **(extra or {})}
    rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    return r


def scale15(bars, w, cost=7.5):
    cfg = EN.Config(cost_bps=cost)
    d = EN.to_daily(EN.run(bars, w, cfg)["bars"], bars.freq)
    k = 0.15 / (d.loc[DEV[0]:DEV[1], "net"].std() * np.sqrt(365))
    w = w * k
    return w, EN.to_daily(EN.run(bars, w, cfg)["bars"], bars.freq)


def own_size(bars, sig, members=None, n=10):
    lr = np.log(bars.close).diff()
    vol = lr.rolling(30, min_periods=20).std() * np.sqrt(365)
    hist = bars.close.notna().cumsum() >= 200
    w = (sig.reindex_like(bars.close).fillna(0).clip(-2, 2) * (0.40 / vol).clip(upper=1.0)).where(hist, 0.0).fillna(0.0)
    if members is not None:
        w = w.where(members, 0.0)
    return w / n


# ---------------- H1 point-in-time universe on Yahoo data
yb = D._lab_file(D.LAB / "crypto_pit_yahoo_1d.parquet")
yb.close = yb.close.where(yb.close > 0)
cs = S.CStarTrend(); ysig = cs.signal(yb, cs.defaults())
dv = (yb.volume).rolling(30, min_periods=20).mean().shift(1)
eligible = yb.close.notna().cumsum().shift(1) >= 200
mfirst = ~yb.close.index.to_period("M").duplicated()
def members(n):
    rk = dv.where(eligible).rank(axis=1, ascending=False)
    m = (rk <= n)[mfirst].reindex(yb.close.index).ffill().fillna(False).astype(bool)
    return m
MAJ = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]
fixed = pd.DataFrame(False, index=yb.close.index, columns=yb.symbols); fixed[MAJ] = True
for tag, mem, n in (("H1 fixed 10 majors (Yahoo data)", fixed, 10), ("H1 point-in-time top 10 by volume", members(10), 10),
                    ("H1 point-in-time top 20 by volume", members(20), 20)):
    w, d = scale15(yb, own_size(yb, ysig, mem, n))
    held = mem.loc["2018-03-05":]
    summ(tag, d["net"], {"avg_members_traded": float((w.loc["2018-03-05":].abs() > 0).sum(axis=1).mean())})
m10 = members(10)
print("PIT top-10 membership share by coin (2018+):", (m10.loc["2018":].mean().sort_values(ascending=False).head(25).round(2)).to_dict(), flush=True)

# ---------------- base C* (Binance) at 15% vol, as in Gen52
CR = G.CR
base_sig = cs.signal(CR, cs.defaults())
w0, d0 = G.backtest(base_sig, 30, 0.0)
base = summ("C* base (Binance, vol30)", d0["net"])

# ---------------- H3 AHL / Baz et al. continuous trend signal
def ahl(c):
    out = 0
    for s_, l_ in ((8, 24), (16, 48), (32, 96)):
        x = c.ewm(halflife=np.log(0.5) / np.log(1 - 1 / s_), adjust=False).mean() - c.ewm(halflife=np.log(0.5) / np.log(1 - 1 / l_), adjust=False).mean()
        y = x / c.rolling(63, min_periods=40).std()
        z = y / y.rolling(252, min_periods=120).std()
        out = out + z * np.exp(-z ** 2 / 4) / 0.89
    return (out / 3).clip(lower=0).fillna(0)
sig_ahl = S.per_asset(CR, ahl)
_, d3 = G.backtest(sig_ahl, 30, 0.0); summ("H3 AHL trend signal alone", d3["net"])
w3b, d3b = G.backtest((base_sig + sig_ahl) / 2, 30, 0.0); r3b = summ("H3 C* + AHL 50/50", d3b["net"])

# ---------------- H4 portfolio vol target (EWMA covariance)
ret = CR.close.pct_change(fill_method=None).fillna(0.0)
lam = 0.5 ** (1 / 60); cov = np.zeros((ret.shape[1], ret.shape[1])); R = ret.to_numpy(); W0 = w0.reindex(ret.index).fillna(0.0).to_numpy()
k = np.ones(len(R))
for t in range(len(R)):
    if t > 60:
        pv = np.sqrt(W0[t] @ cov @ W0[t] * 365)
        k[t] = min(2.0, 0.15 / pv) if pv > 0 else 1.0
    cov = lam * cov + (1 - lam) * np.outer(R[t], R[t])
w4 = w0.mul(pd.Series(k, index=ret.index), axis=0)
d4 = EN.to_daily(EN.run(CR, w4, EN.Config(cost_bps=7.5))["bars"], "1d"); r4 = summ("H4 C* + portfolio vol target (cap 2x)", d4["net"])

# ---------------- H5 BTC leads
s5 = base_sig.copy(); alts = [c for c in s5.columns if c != "BTC"]
s5[alts] = s5[alts].where(base_sig["BTC"] > 0, 0.0, axis=0)
w5, d5 = G.backtest(s5, 30, 0.0); r5 = summ("H5 C* alts only when BTC trend is up", d5["net"])

# ---------------- H2 tranching on OKX hourly
ok = D._okx_local().select(MAJ)
def okx_daily(h):
    sh = pd.Timedelta(hours=h)                                     # daily bars starting at h:00 UTC (shift, resample, shift back)
    def rs(df, how):
        x = df.copy(); x.index = x.index - sh; y = getattr(x.resample("1D"), how)() if how != "sum" else x.resample("1D").sum(min_count=1)
        y.index = y.index + sh; return y
    o, hi, lo, c, v = rs(ok.open, "first"), rs(ok.high, "max"), rs(ok.low, "min"), rs(ok.close, "last"), rs(ok.volume, "sum")
    keep = c.notna().any(axis=1)
    return D.Bars(f"okx d{h}", "1d", o[keep], hi[keep], lo[keep], c[keep], v[keep], 365.0, {})
def hourly_weights(h):
    db = okx_daily(h); sg = cs.signal(db, cs.defaults())
    wd = EN.size(db, sg, EN.Config())
    wd.index = wd.index + pd.Timedelta(hours=23)                  # decided at the close of the daily bar = close of its last hour
    return wd.reindex(ok.close.index.union(wd.index)).ffill().reindex(ok.close.index).fillna(0.0)
W2 = {h: hourly_weights(h) for h in (0, 6, 12, 18)}
for tag, wh in (("H2 single schedule 00 UTC (OKX hourly)", W2[0]), ("H2 four tranches 00/06/12/18 UTC", sum(W2.values()) / 4)):
    w_, d_ = scale15(ok, wh)
    rr = summ(tag, d_["net"], {"turnover_per_day": float(EN.run(ok, w_, EN.Config())["bars"]["turnover"].sum() / max(1, len(d_)))})
    if tag.startswith("H2 single"):
        h2_base, d2_base = rr, d_
    else:
        h2_t, d2_t = rr, d_

passed = {"H3": r3b["sharpe_test"] >= base["sharpe_test"] + 0.10 and r3b["max_dd"] >= base["max_dd"],
          "H4": r4["sharpe_test"] >= base["sharpe_test"] + 0.10 and r4["max_dd"] >= base["max_dd"],
          "H5": r5["sharpe_test"] >= base["sharpe_test"] + 0.10 and r5["max_dd"] >= base["max_dd"],
          "H2": h2_t["sharpe_test"] >= h2_base["sharpe_test"] + 0.10 and h2_t["max_dd"] >= h2_base["max_dd"]}
print("PASSED:", passed, flush=True)
for tag, d_ in (("H2 single 00 UTC", d2_base), ("H2 four tranches", d2_t)):
    x = d_.loc["2021-01-01":]
    for fn, f in G.FIRMS.items():
        a = PF.attempts(x, f, 1.0); p = PF.pipeline(x, f, 5, 1, 1.0, 0.4, horizon_days=730, step=5)
        print(f"PROP (OKX hourly path, 2021+) {tag:18s} {fn}: pass {a['P_pass']:.0%} net {p['net_mean']:7.0f} p50 {p['net_p50']:7.0f} P(profit) {p['P_profit']:.0%}", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen53_research.csv", index=False)
