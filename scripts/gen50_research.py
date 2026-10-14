"""Gen50 (config/gen50_protocol.json). Writes results/gen50_research.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, analysis as A, futures_curve as FC, propfirms as PF, scorecard as SC
from qpl.lab import strategies as S
from qpl.lab.strategies_papers import NoiseAreaMomentum, VolatilityManaged, CurveMomentum
from qpl.data import loaders as L

rows = []; SRC = D.list_sources(); N_TRIALS = 280


def report(tag, d, extra=None):
    x = d["net"]; ppy = D.periods_per_year(x.index, "1d"); Sm = A.summary(x, ppy)
    row = {"test": tag, "sharpe": Sm["Sharpe"], "cagr": Sm["CAGR"], "vol": Sm["Volatility"], "max_dd": Sm["Max drawdown"],
           "calmar": Sm["Calmar"], "pos_months": Sm["Positive months"], "worst_month": Sm["Worst month"], "years": Sm["Years"],
           "from": x.index[0].date(), "to": x.index[-1].date(), "dsr": A.dsr(x, ppy, N_TRIALS), **(extra or {})}
    rows.append(row); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    return row


cr = SRC["Binance spot majors (daily, 2017+)"]()
cfg = EN.Config(cost_bps=7.5, leverage=0.79)
cs = S.CStarTrend(); sig_c = cs.signal(cr, cs.defaults())
cct = S.CryptoTrendEnsemble(); sig_t = cct.signal(cr, cct.defaults())


def crypto_daily(sig):
    r = EN.run(cr, EN.size(cr, sig, cfg), cfg); return EN.to_daily(r["bars"], "1d").loc["2018-03-05":]


dC = crypto_daily(sig_c); base = report("C* (baseline)", dC)
dT = crypto_daily(sig_t); report("G50a CCT ensemble (10 majors)", dT, {"corr_with_Cstar": float(dC["net"].corr(dT["net"]))})
dB = crypto_daily((sig_c + sig_t) / 2); rB = report("G50b C* + CCT 50/50", dB)
passed = {"G50b": rB["sharpe"] >= base["sharpe"] + 0.10 and rB["max_dd"] >= base["max_dd"]}

# G50d equity regime
fut = SRC["Futures daily, 250 markets (pysystemtrade, to 2024-03)"]()
sp = fut.close["SP500"].dropna()
on = (sp > sp.rolling(200).mean()).astype(float).shift(1)          # yesterday's regime
mult = on.reindex(pd.date_range(sp.index[0], cr.close.index[-1])).ffill().reindex(cr.close.index).fillna(1.0).map({1.0: 1.0, 0.0: 0.5})
end = sp.index[-1]
dR = crypto_daily(sig_c.mul(mult, axis=0)).loc[:end]
bC = report("C* baseline to 2024-03 (S&P data end)", dC.loc[:end])
rR = report("G50d C* x S&P 200-day regime (x1 / x0.5)", dR)
passed["G50d"] = rR["sharpe"] >= bC["sharpe"] + 0.10 and rR["max_dd"] >= bC["max_dd"]

# G50c Sharpe-weighted multi-strategy
def daily_of(b, st, p, cost, lev=1.0, start=None, weekdays=True):
    s_ = st.signal(b, p); c_ = EN.Config(cost_bps=cost, leverage=lev)
    r_ = EN.run(b, EN.size(b, s_, c_, getattr(st, "sizing", "engine")), c_)
    d_ = EN.to_daily(r_["bars"], b.freq); nz = (s_ != 0).any(axis=1)
    t0 = max(s_.index[nz][0].floor("D"), pd.Timestamp(start)) if start else s_.index[nz][0].floor("D")
    d_ = d_.loc[t0:]
    return d_[d_.index.dayofweek < 5] if weekdays else d_


x = L.raw_dukascopy("US100", "M15"); x.index = x.index.tz_localize(None); f1 = lambda k: x[[k]].rename(columns={k: "US100"})
us100 = D.Bars("US100", "15m", f1("open"), f1("high"), f1("low"), f1("close"), f1("volume"), D.periods_per_year(x.index, "15m"))
sleeves = {"C*": dC,
           "noise-area US100": daily_of(us100, NoiseAreaMomentum(), NoiseAreaMomentum().defaults(), 1.0),
           "vol-managed SP500": daily_of(fut.select(["SP500"], start="1990-01-01"), VolatilityManaged(), VolatilityManaged().defaults(), 1.0, start="1991-01-01"),
           "curve momentum": daily_of(FC.bars().select(start="1995-01-01"), CurveMomentum(), CurveMomentum().defaults(), 8.0, lev=0.5, start="2000-01-01", weekdays=False)}
prior = pd.Series({"C*": 1.67, "noise-area US100": 0.71, "vol-managed SP500": 0.63, "curve momentum": 0.37})
t0, t1 = pd.Timestamp("2018-09-01"), pd.Timestamp("2023-09-11")
cal = pd.date_range(t0, t1, freq="D"); hc = pd.date_range("2017-09-01", t1, freq="D")
hist = pd.DataFrame({k: v["net"] for k, v in sleeves.items()}).reindex(hc).fillna(0.0)
vol = hist.rolling(365, min_periods=180).std() * np.sqrt(365)
mfirst = ~hc.to_period("M").duplicated()
raw = (prior / vol).shift(1)[mfirst].reindex(hc).ffill()
wraw = raw.div(raw.sum(axis=1), axis=0)
pv = (hist * wraw).sum(axis=1).rolling(365, min_periods=180).std() * np.sqrt(365)
lev = (0.15 / pv).shift(1)[mfirst].reindex(hc).ffill().clip(upper=3.0)
W = wraw.mul(lev, axis=0).reindex(cal)
R = {k: v.reindex(cal).fillna(0.0) for k, v in sleeves.items()}
port = pd.DataFrame({c_: sum(R[k][c_] * W[k] for k in R) for c_ in ("net",)})
port["worst"] = sum(R[k]["worst"].clip(upper=0) * W[k] for k in R); port["best"] = sum(R[k]["best"].clip(lower=0) * W[k] for k in R)
cw = dC.reindex(cal).fillna(0.0)
bw = report("C* same window 2018-09..2023-09", cw)
rM = report("G50c Sharpe-weighted multi-strategy (15% vol)", port, {"avg_weights": str(W.mean().round(2).to_dict())})
passed["G50c"] = rM["sharpe"] >= bw["sharpe"] + 0.10 and rM["max_dd"] >= bw["max_dd"]

print("PASSED:", passed, flush=True)
for nm, dd in (("C*", dC), ("C*+CCT", dB)):
    for firm in ("Crypto Fund Trader 1-Phase $100k", "FTMO 2-Step $100k"):
        f = PF.PRESETS[firm]; a = PF.attempts(dd, f); p = PF.pipeline(dd, f, 5, 1, 1.0, 0.4, horizon_days=730)
        print(f"PROP {nm:8s} {firm:33s} pass {a['P_pass']:.0%} funded {p['P_funded']:.0%} net {p['net_mean']:8.0f} p50 {p['net_p50']:8.0f} P(profit) {p['P_profit']:.0%}", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen50_research.csv", index=False)
