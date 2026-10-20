"""Gen134 (config/gen134_protocol.json): noise-area variants; select on 2018-2023, judge once on 2024-26 and NQ 2010-17.
Writes results/gen134.json."""
import json
import shutil
import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen125_futures_intraday.py").read()
g = {"__file__": str(ROOT / "scripts/gen125_futures_intraday.py")}
exec(src.split("\nB5 = {r: bars5(r)")[0], g)
F, bars5, sharpe, D, EN, NoiseAreaMomentum = (g[k] for k in ("F", "bars5", "sharpe", "D", "EN", "NoiseAreaMomentum"))
VAR = {"V0": {}, "V1": {"check_minutes": 60}, "V2": {"band_mult": 1.5}, "V3": {"vwap_stop": False}, "V4": {"allow_short": False}}


def run(d, root, cost_bp, params):
    w = {k: d[[k]].rename(columns={k: root}) for k in ("open", "high", "low", "close", "volume")}
    b = D.Bars(f"{root} 5m", "5m", *(w[k] for k in ("open", "high", "low", "close", "volume")), periods_per_year=D.periods_per_year(d.index, "5m"))
    st = NoiseAreaMomentum(); p = {**st.defaults(), **params}; sig = st.signal(b, p)
    cfg = EN.Config(cost_bps=cost_bp); r = EN.run(b, EN.size(b, sig, cfg, "raw"), cfg)
    dd = EN.to_daily(r["bars"], b.freq)["net"]; dd = dd[dd.index >= dd.index[0] + pd.Timedelta(days=21)]
    return dd[dd.index.dayofweek < 5]


def cost(root, a, b):
    dd = F.daily(root).loc[a:b]; return float(F.cost_frac(root, dd.close).median() * 1e4)


B5 = {r: bars5(r) for r in ("ES", "NQ")}
C = {r: cost(r, "2018", "2026-09") for r in B5}
tmp = Path(tempfile.mkdtemp()); shutil.copy(F.DB / "NQ_1m_2010_2017.parquet", tmp / "NQ_1m.parquet"); real = F.DB; F.DB = tmp
NQ_OLD = bars5("NQ"); F.DB = real
C_OLD = cost("NQ", "2010-06", "2017-12")
avg = lambda xs: pd.concat(xs, axis=1).fillna(0.0).mean(axis=1)
dev = {}
for k, prm in VAR.items():
    p = avg([run(B5[r], r, C[r], prm) for r in B5]); dev[k] = (round(sharpe(p, "2018-01-01", "2023-12-31"), 3), p)
    print(k, prm, "DEV 2018-23:", dev[k][0], flush=True)
best = max(dev, key=lambda k: dev[k][0])
p = dev[best][1]; hold = round(sharpe(p, "2024-01-01", "2026-09-30"), 3)
old = run(NQ_OLD, "NQ", C_OLD, VAR[best]).loc["2010-06-01":"2017-12-31"]; oos = round(sharpe(old, "2010-06-01", "2017-12-31"), 3)
out = {"costs bp": {**{k: round(v, 2) for k, v in C.items()}, "NQ 2010-17": round(C_OLD, 2)}, "DEV 2018-23 by variant": {k: v[0] for k, v in dev.items()},
       "selected": best, "judgement: ES+NQ 2024-26": hold, "judgement: NQ 2010-17": oos, "pass": bool(hold >= 0.5 and oos >= 0.3)}
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen134.json", "w"), indent=1)
pd.DataFrame({"selected 2018-26": p}).to_parquet(ROOT / "results/gen134_daily.parquet")
