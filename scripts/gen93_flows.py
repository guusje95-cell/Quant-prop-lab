"""Gen93 (config/gen93_protocol.json): stablecoin mint spike, perp deep-discount bounce, funding flush bounce.
Writes results/gen93.csv and results/cache_gen93_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
B, CFD, fhp, d2h, IDX, report, hold_w, P, R = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "report", "hold_w", "P", "R"))
from qpl.lab.data import stablecoin_caps

caps = stablecoin_caps(); caps = caps.where(caps > 0); caps.index = pd.DatetimeIndex(caps.index).normalize()
gr = (caps / caps.shift(1) - 1).shift(2).reindex(P.index)              # known at the close of d with the 2-day lag
w = pd.DataFrame(0.0, index=P.index, columns=CFD)
for c in ("BTC", "ETH"):
    w[c] = hold_w(gr > 0.005, hold=3).to_numpy()
w.loc["2026-05-25":] = 0.0
g["report"]("M1 stablecoin mint spike (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), extra={"signal days": int((gr > 0.005).sum())})

w = pd.DataFrame(0.0, index=P.index, columns=CFD); nsig = 0
for c in ("BTC", "ETH"):
    pm = B.premium(c)["close"]; pd_ = pm.groupby(pm.index.floor("D")).mean().reindex(P.index)
    q = pd_.shift(1).rolling(365, min_periods=180).quantile(0.05)
    s = pd_ < q; nsig += int(s.sum()); w[c] = hold_w(s).to_numpy()
g["report"]("M2 perp deep-discount bounce (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), extra={"signal days": nsig})

w = pd.DataFrame(0.0, index=P.index, columns=CFD); nsig = 0
for c in ("BTC", "ETH"):
    f = B.funding(c); f = f[(f.index.hour.isin([0, 8, 16])) & (f.index.minute == 0)]
    allneg = (f < 0).groupby(f.index.floor("D")).agg(lambda x: bool(len(x) == 3 and x.all())).reindex(P.index).fillna(False).astype(bool)
    s = allneg & (P[c] / P[c].shift(3) - 1 < 0); nsig += int(s.sum()); w[c] = hold_w(s).to_numpy()
g["report"]("M3 funding flush bounce (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), extra={"signal days": nsig})
pd.DataFrame(g["CANDS"]).to_parquet(ROOT / "results/cache_gen93_hourly.parquet")
pd.DataFrame(g["ROWS"]).to_csv(ROOT / "results/gen93.csv", index=False)
print("done", flush=True)
