"""Gen440 (config/gen440_protocol.json, FLAGGED): follow the market-wide alt premium. Writes results/gen440.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen439_alt_froth.py").read().split("\nZF, ZP = ")[0]
g = {"__file__": str(ROOT / "scripts/gen439_alt_froth.py")}; exec(compile(src, "g439", "exec"), g)
CS, BL, LL, V, idx, unit, shp, per, dd, days, Q, Pd, age = (g[k] for k in ("CS", "BL", "LL", "V", "idx", "unit", "shp", "per", "dd", "days", "Q", "Pd", "age"))
v30 = Q.rolling(30, min_periods=20).sum().shift(1)
def zser(n=100, smooth=7, lag=0):
    mem = v30.where(age.shift(1) >= 60).rank(axis=1, ascending=False) <= n; w = v30.where(mem)
    X = Pd.where(mem); ww = w.where(X.notna()); a = (X * ww).sum(axis=1) / ww.sum(axis=1)
    x = a.rolling(smooth, min_periods=max(2, smooth - 2)).mean()
    return ((x - x.rolling(365, min_periods=250).mean()) / x.rolling(365, min_periods=250).std()).shift(1 + lag)
mk = lambda z: (lambda: pd.DataFrame({"BTC": 0.125 * z.clip(-2, 2) / 2, "ETH": 0.125 * z.clip(-2, 2) / 2}).fillna(0.0))
mem_pnl = lambda z, cm=5: CS._from_daily_weights(mk(z)().reindex(days).fillna(0.0), ["BTC", "ETH"], cm).reindex(idx).fillna(0.0)
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
bk0, _ = BL.basket(idx); r0 = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
z = zser(); base = list(BL.MEMBERS); BL.BUILD["follow froth"] = mk(z); BL.MEMBERS = base + ["follow froth"]; bk, _ = BL.basket(idx); BL.MEMBERS = base
b = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk}))[0]); r = [shp(b), per(b)]
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
m = mem_pnl(z)
out = {"reference v9.6 (live timing)": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]], "member": per(m),
       "by year": {str(y): shp(m, str(y), str(y)) for y in range(2022, 2027)}, "corr basket": round(float(dd(m).corr(dd(bk0))), 2),
       "corr BTC daily return": round(float(dd(m).corr(dd(CS._from_daily_weights(pd.DataFrame({"BTC": 1.0}, index=days), ["BTC"], 0).reindex(idx).fillna(0.0)))), 2),
       "basket": per(bk), "book": r, "pass": bool(ok(r, REF) and ok(r, REF2)),
       "robustness": {"costs x2": per(mem_pnl(z, 10)), "one day later": per(mem_pnl(zser(lag=1))), "smooth 3": per(mem_pnl(zser(smooth=3))),
                      "smooth 14": per(mem_pnl(zser(smooth=14))), "top 50": per(mem_pnl(zser(n=50))), "top 200": per(mem_pnl(zser(n=200)))}}
(ROOT / "results/gen440.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
