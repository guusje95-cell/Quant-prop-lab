"""Gen409 (config/gen409_protocol.json). Writes results/gen409.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
dd, shp, per, unit, END, CS, V, B, pnl8, rc6, a, bsm = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "B", "pnl8", "rc6", "a", "bsm"))
V5 = V.assign(**{"relative crowding 6": (rc6 + a + bsm) / 3}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
def z8(c, col):
    m = B.metrics(c)[col]; m.index = pd.DatetimeIndex(m.index); x = m.resample("8h").mean()
    return (x - x.rolling(270, min_periods=190).mean()) / x.rolling(270, min_periods=190).std()
W = pd.DataFrame({c: -0.125 * ((z8(c, "count_toptrader_long_short_ratio") + z8(c, "count_long_short_ratio")) / 2).clip(-2, 2) / 2 for c in ("BTC", "ETH")}).fillna(0.0)
s = pnl8(W).reindex(V.index).fillna(0.0)
b = unit(CS.portfolio_v5(V5.assign(**{"directional crowding 8h": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.5": [REF[0], REF[1]], "sleeve": per(s), "corr v9.5": round(float(pd.concat([dd(s), dd(v95)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
       "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen409.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
