"""Gen126 (config/gen126_protocol.json): NQ noise-area breakout on unseen 2010-06..2017-12 NQ 1-minute data, exact Gen125 K1 code.
Writes results/gen126.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen125_futures_intraday.py").read()
g = {"__file__": str(ROOT / "scripts/gen125_futures_intraday.py")}
exec(src.split("\nB5 = {r: bars5(r)")[0], g)
F, bars5, noise, sharpe = g["F"], g["bars5"], g["noise"], g["sharpe"]
F.DB = Path(F.DB)
import shutil, tempfile                                                    # bars5 reads {root}_1m.parquet: point it at the 2010-17 file
tmp = Path(tempfile.mkdtemp()); shutil.copy(F.DB / "NQ_1m_2010_2017.parquet", tmp / "NQ_1m.parquet")
real_db = F.DB; F.DB = tmp
g["B5"] = {"NQ": bars5("NQ")}
F.DB = real_db
dd = F.daily("NQ").loc["2010-06":"2017-12"]
cost = float(F.cost_frac("NQ", dd.close).median() * 1e4)
p = noise("NQ", cost).loc["2010-06-01":"2017-12-31"]
out = {"cost bp/side": round(cost, 3),
       "2010-06..2017-12": round(sharpe(p, "2010-06-01", "2017-12-31"), 3),
       "first half 2010-06..2013-12": round(sharpe(p, "2010-06-01", "2013-12-31"), 3),
       "second half 2014..2017": round(sharpe(p, "2014-01-01", "2017-12-31"), 3),
       "fully unseen 2010-06..2013-07": round(sharpe(p, "2010-06-01", "2013-07-31"), 3),
       "by year": {int(y): round(float(x.mean() / x.std() * np.sqrt(252)), 2) for y, x in p[p.index.weekday < 5].groupby(p.index[p.index.weekday < 5].year)},
       "ann return": round(float(p.mean() * 252), 4), "active days": int((p != 0).sum())}
out["pass"] = bool(out["2010-06..2017-12"] >= 0.5 and out["first half 2010-06..2013-12"] > 0 and out["second half 2014..2017"] > 0
                   and out["fully unseen 2010-06..2013-07"] > 0)
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen126.json", "w"), indent=1)
p.to_frame("pnl").to_parquet(ROOT / "results/gen126_daily.parquet")
