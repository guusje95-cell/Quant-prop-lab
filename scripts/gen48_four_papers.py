"""Gen48: pre-registered tests of four papers (config/gen48_four_papers_protocol.json). Writes results/gen48_four_papers.csv."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, analysis as A, futures_curve as FC
from qpl.lab.strategies_papers import SemivarianceTSMOM, VolatilityManaged, EuropeanOpen, CurveMomentum
from qpl.data import loaders as L

rows = []


def run(tag, b, st, p, cost, lev=1.0, start=None, split=None):
    t = time.time()
    sig = st.signal(b, p); cfg = EN.Config(cost_bps=cost, leverage=lev)
    r = EN.run(b, EN.size(b, sig, cfg, "raw"), cfg)
    d = EN.to_daily(r["bars"], b.freq)["net"]
    nz = (sig != 0).any(axis=1)
    t0 = max(pd.Timestamp(start) if start else pd.Timestamp("1900-01-01"), sig.index[nz][0].floor("D") if nz.any() else d.index[0])
    d = d.loc[t0:]
    if b.freq != "1d" or "CFD" in tag:
        d = d[d.index.dayofweek < 5] if "crypto" not in tag else d
    ppy = D.periods_per_year(d.index, "1d")
    S = A.summary(d, ppy)
    row = {"test": tag, "cost_bp": cost, "sharpe": S["Sharpe"], "cagr": S["CAGR"], "vol": S["Volatility"], "max_dd": S["Max drawdown"],
           "pos_months": S["Positive months"], "years": S["Years"], "from": d.index[0].date(), "to": d.index[-1].date()}
    if split:
        a, z = A.split_stats(d, ppy, pd.Timestamp(split)); row["sharpe_h1"] = a.get("Sharpe"); row["sharpe_h2"] = z.get("Sharpe")
    rows.append(row)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, f"{time.time() - t:.0f}s", flush=True)
    return d


# ---------------- G48a semivariance TSMOM: 13 Dukascopy CFDs hourly, OKX perps hourly
syms = list(L.CFG["dukascopy_github"]["files"])
fr = {}
for s in syms:
    x = L.raw_dukascopy(s, "H1"); x.index = x.index.tz_localize(None); fr[s] = x
w = {k: pd.DataFrame({s: fr[s][k] for s in syms}).sort_index() for k in ("open", "high", "low", "close", "volume")}
cfd = D.Bars("Dukascopy 13 CFDs H1", "1h", w["open"], w["high"], w["low"], w["close"], w["volume"], 0.0).select(start="2013-06-01")
cfd.periods_per_year = D.periods_per_year(cfd.close.index, "1h")
st = SemivarianceTSMOM()
for mode in ("TSM (no semivariance filter)", "TTSM-S1", "TTSM-S2 (paper best)"):
    run(f"G48a CFD13 {mode}", cfd, st, dict(st.defaults(), mode=mode), 2.0, 0.25, split="2018-07-01")
okx = D.list_sources()["OKX USDT perps (hourly, 2020+)"]()
for mode in ("TSM (no semivariance filter)", "TTSM-S2 (paper best)"):
    run(f"G48a crypto OKX {mode}", okx, st, dict(st.defaults(), mode=mode), 7.5, 0.25, split="2023-01-01")

# ---------------- G48b vol-managed: SP500 + 6 indices (futures), BTC
fut = D.list_sources()["Futures daily, 250 markets (pysystemtrade, to 2024-03)"]()
vm = VolatilityManaged()
from qpl.lab.strategies import BuyHold
bh = BuyHold()
for idx_ in ("SP500", "NASDAQ", "DOW", "DAX", "EUROSTX", "FTSE100", "NIKKEI"):
    b = fut.select([idx_], start="1990-01-01")
    run(f"G48b {idx_} buy&hold", b, bh, {}, 1.0, 1.0, start="1991-01-01")
    run(f"G48b {idx_} vol-managed", b, vm, vm.defaults(), 1.0, 1.0, start="1991-01-01")
    if idx_ == "SP500":
        run(f"G48b {idx_} vol-managed cap1.5", b, vm, dict(vm.defaults(), max_leverage=1.5), 1.0, 1.0, start="1991-01-01")
cr = D.list_sources()["Binance spot majors (daily, 2017+)"]().select(["BTC"])
run("G48b BTC buy&hold crypto", cr, bh, {}, 7.5, 1.0, start="2018-09-01")
run("G48b BTC vol-managed crypto", cr, vm, vm.defaults(), 7.5, 1.0, start="2018-09-01")

# ---------------- G48c European open
eo = EuropeanOpen()
for s, src in (("US500", "US500 CFD, Dukascopy (15-min)"), ("US100", "US100 CFD, Dukascopy (15-min)")):
    b = D.list_sources()[src]()
    for cost in ((1.0, 0.3, 2.0) if s == "US500" else (1.0,)):
        run(f"G48c EUopen {s} CFD", b, eo, eo.defaults(), cost, split="2018-09-01")
for s in ("US30", "DE40"):
    x = L.raw_dukascopy(s, "M15"); x.index = x.index.tz_localize(None)
    f1 = lambda k: x[[k]].rename(columns={k: s})
    b = D.Bars(s, "15m", f1("open"), f1("high"), f1("low"), f1("close"), f1("volume"), D.periods_per_year(x.index, "15m"))
    run(f"G48c EUopen {s} CFD", b, eo, eo.defaults(), 1.0, split="2018-09-01")
cme = D.list_sources().get("Downloaded: cme_futures_5min")
if cme:
    b = D.resample(cme().select(["ES"]), "15m")
    run("G48c EUopen ES real futures 2026 (3 months)", b, eo, eo.defaults(), 0.3)

# ---------------- G48d curve momentum
cb = FC.bars().select(start="1995-01-01")
cm = CurveMomentum()
for mode in ("generic (nearest contract)", "optimal-roll (paper)"):
    run(f"G48d curve {mode}", cb, cm, dict(cm.defaults(), mode=mode), 8.0, 0.5, start="2000-01-01", split="2012-01-01")

out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen48_four_papers.csv", index=False)
print(out.round(3).to_string())
