"""Gen398 (config/gen398_protocol.json). Writes results/gen398.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, z, daily, B, pnl, days, rel = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "z", "daily", "B", "pnl", "days", "rel"))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
V4 = V.assign(**{"relative crowding 6": rc6}); v94 = unit(CS.portfolio_v5(V4)[0]); REF = (shp(v94), per(v94))
pk = B.coins(); qv = pd.DataFrame({c: B.k5(c).quote_volume.resample("1D").sum() for c in pk}).reindex(days)
mem = (qv.rolling(30, min_periods=20).sum().shift(1).rank(axis=1, ascending=False) <= 10)
mem = mem[~mem.index.to_period("M").duplicated()].reindex(days).ffill().fillna(False)
def relp(col):
    Z = pd.DataFrame({c: z(daily(B.metrics(c)[col], "mean"), 90) for c in pk}).where(mem)
    Zd = Z.sub(Z.mean(axis=1), axis=0); return (-0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)
cols = ["count_toptrader_long_short_ratio", "count_long_short_ratio"]
T = {"T1 point-in-time top-10": sum(pnl(relp(c)) for c in cols) / 2,
     "T2 + top-trader positions": sum(pnl(rel(C6, c)) for c in cols + ["sum_toptrader_long_short_ratio"]) / 3,
     "T3 + taker flow contrarian": sum(pnl(rel(C6, c)) for c in cols + ["sum_taker_long_short_vol_ratio"]) / 3}
out = {"reference v9.4": [REF[0], REF[1]], "trials": {}}
for k, s in T.items():
    s = s.reindex(V.index).fillna(0.0); b = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen398.json").write_text(json.dumps(out, indent=1))
