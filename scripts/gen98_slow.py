"""Gen98 (config/gen98_protocol.json): weekly deleveraging bounce and gold 12-month trend. Writes results/gen98.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
B, CFD, fhp, d2h, IDX, P, report, dsh = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "P", "report", "dsh"))
days = P.index; t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
w = pd.DataFrame(0.0, index=days, columns=CFD); n = 0
for c in ("BTC", "ETH"):
    m = B.metrics(c)["sum_open_interest_value"]; m = m.where(m > 0).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
    s = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=7)) - 1 < -0.20) & (f(px, t) < f(px, t - pd.Timedelta(days=7))), index=days)
    s.loc[:"2021-12-08"] = False; n += int(s.sum())
    w[c] = s.astype(float).rolling(5, min_periods=1).max().to_numpy() * 0.5
report("W1 weekly deleveraging bounce (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), dev=("2022-01-01", "2022-12-31"), extra={"signal days": n})

x = pd.read_parquet(ROOT / "research_data/dukascopy/XAUUSD_1h.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index()
o = x.open; c = x.close.resample("1D").last().dropna(); c = c[c.index.dayofweek < 5]
r = c.pct_change(); sig = (c.shift(1) / c.shift(253) - 1 > 0).astype(float)
lev = (0.10 / (r.rolling(60).std().shift(1) * np.sqrt(252))).clip(upper=2.0)
wd = (sig * lev).fillna(0.0)                                                    # weight for day d, from data to d-1 close
hidx = pd.date_range("2013-01-01", "2026-09-30 23:00", freq="1h")
pos = wd.reindex(hidx.floor("D")).set_axis(hidx).fillna(0.0)
pos = pos.where(hidx.floor("D").isin(wd.index), np.nan).ffill().fillna(0.0)     # weekends: keep Friday's weight
oo = o.reindex(hidx).ffill(); hr = (oo.shift(-1) / oo - 1).fillna(0.0)
gold = (pos * hr - pos.diff().abs().fillna(0.0) * 2.0 / 1e4 - pos * 0.03 / (365 * 24)).shift(1).fillna(0.0)
y = pd.read_parquet(ROOT / "data/raw/yahoo/GOLD.parquet")["close"]; y.index = pd.DatetimeIndex(y.index).normalize(); yr = y.pct_change()
ys = (y.shift(1) / y.shift(253) - 1 > 0).astype(float) * (0.10 / (yr.rolling(60).std().shift(1) * np.sqrt(252))).clip(upper=2.0)
yp = (ys * yr - ys.diff().abs() * 2e-4 - ys * 0.03 / 252).loc["2005-11":"2012-12"].dropna()
report("Y1 gold 12-month trend (PRIMARY)", gold.reindex(IDX.union(hidx)).fillna(0.0), dev=("2014-01-01", "2019-12-31"), test=("2020-01-01", "2023-12-31"),
       hold=("2024-01-01", "2026-09-30"), extra={"pre-check 2005-12 Sharpe (Yahoo)": float(yp.mean() / yp.std() * np.sqrt(252)), "time in market": float((wd > 0).mean())})
pd.DataFrame(g["ROWS"]).to_csv(ROOT / "results/gen98.csv", index=False)
print("done", flush=True)
