"""Gen219 (config/gen219_protocol.json): 2003-2010 backcast of BC and F3 on the Dukascopy US T-bond CFD. Writes results/gen219.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "research_data/dukascopy_daily/USTBONDTRUSD_D1_raw.parquet"); d = d[d.index.weekday < 5]
r = d.close.pct_change(); A, Z = "2003-06-01", "2010-05-31"


def pnl(w):
    w = w.reindex(r.index).fillna(0.0); return (w * r - w.diff().abs().fillna(w.abs()) * 1e-4).loc[A:Z]


z = r / r.rolling(60, min_periods=40).std().shift(1)
bc = pd.Series(np.where(z.abs() > 2, np.sign(r), 0.0), index=r.index).shift(1).rolling(3, min_periods=1).mean().shift(1)
f3 = pd.Series(0.0, index=r.index)
for _, g in r.index.to_series().groupby(r.index.to_period("M")):
    f3.loc[g.index[-3:]] = 1.0
sh = lambda x: round(float(x.mean() / x.std() * np.sqrt(252)), 3)
S = {"BC": pnl(bc), "F3": pnl(f3)}
out = {"window": [A, Z], "data": [str(d.index.min().date()), str(d.index.max().date())], "per sleeve": {k: sh(v) for k, v in S.items()},
       "per year": {k: {str(y): sh(v.loc[str(y)]) for y in range(2003, 2011)} for k, v in S.items()}, "buy-and-hold": sh(r.loc[A:Z])}
out["fragile (negative backcast)"] = [k for k, v in out["per sleeve"].items() if v < 0]
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen219.json", "w"), indent=1)
