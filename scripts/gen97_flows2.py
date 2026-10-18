"""Gen97 (config/gen97_protocol.json): taker sell climax, market-wide deleveraging. Writes results/gen97.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
B, CFD, fhp, d2h, IDX, hold_w, P, R, report = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "hold_w", "P", "R", "report"))
DEV = ("2022-01-01", "2022-12-31")
w = pd.DataFrame(0.0, index=P.index, columns=CFD); n = 0
for c in ("BTC", "ETH"):
    tr = B.metrics(c)["sum_taker_long_short_vol_ratio"]; tr = tr.where(tr > 0)
    td = tr.groupby(tr.index.floor("D")).mean().reindex(P.index)
    s = (td < td.shift(1).rolling(365, min_periods=180).quantile(0.05)) & (R[c] < 0); n += int(s.sum()); w[c] = hold_w(s).to_numpy()
report("T1 taker sell climax (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), dev=DEV, extra={"signal days": n})
tot = None
for c in B.coins():
    m = B.metrics(c)["sum_open_interest_value"]; m = m.where(m > 0).resample("1h").last().ffill()
    tot = m if tot is None else tot.add(m, fill_value=np.nan)
tot = tot.dropna()
days = P.index; t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
px = B.k5("BTC").close.resample("1h").last()
s = pd.Series((f(tot, t) / f(tot, t - pd.Timedelta(days=1)) - 1 < -0.08) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=days)
s.loc[:"2021-12-01"] = False
w = pd.DataFrame(0.0, index=P.index, columns=CFD)
for c in ("BTC", "ETH"):
    w[c] = hold_w(s).to_numpy()
report("T2 market-wide deleveraging (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), dev=DEV, extra={"signal days": int(s.sum())})
pd.DataFrame(g["ROWS"]).to_csv(ROOT / "results/gen97.csv", index=False)
print("done", flush=True)
