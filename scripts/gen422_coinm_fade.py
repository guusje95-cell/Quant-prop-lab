"""Gen422 (config/gen422_protocol.json, FLAGGED): fade the COIN-M vs USDT-M taker divergence. Writes results/gen422.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen421_coinm.py").read().split("\nbk0, _ = BL.basket")[0]
g = {"__file__": str(ROOT / "scripts/gen421_coinm.py")}; exec(compile(src, "g421", "exec"), g)
CS, BL, B, V, CM, unit, shp, per, REF = (g[k] for k in ("CS", "BL", "B", "V", "CM", "unit", "shp", "per", "REF"))
def fade(win=90):
    out = {}
    for c in ("BTC", "ETH"):
        cm = np.log(CM[c]["sum_taker_long_short_vol_ratio"].where(lambda s: s > 0)); um = np.log(B.metrics(c)["sum_taker_long_short_vol_ratio"].where(lambda s: s > 0))
        out[c] = -0.125 * BL.z(BL.daily(cm, "mean") - BL.daily(um, "mean"), win).clip(-2, 2) / 2
    return pd.DataFrame(out)
def mem(w, cm=5, lag=0):
    w = w.reindex(BL.DAYS).fillna(0.0).shift(lag).fillna(0.0); return CS._from_daily_weights(w, list(w.columns), cm).reindex(V.index).fillna(0.0)
bk0, _ = BL.basket(V.index); r0 = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
base = list(BL.MEMBERS); BL.BUILD["fade"] = fade; BL.MEMBERS = base + ["fade"]; bk, _ = BL.basket(V.index); BL.MEMBERS = base
b = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk}))[0]); r = [shp(b), per(b)]
ok = lambda R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
m = mem(fade())
out = {"reference v9.5": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]], "member": per(m), "basket": per(bk), "book": r, "pass": bool(ok(REF) and ok(REF2)),
       "by year": {str(y): shp(m, str(y), str(y)) for y in range(2022, 2027)},
       "robustness": {"costs x2": per(mem(fade(), 10)), "one day later": per(mem(fade(), 5, 1)), "z 60": per(mem(fade(60))), "z 180": per(mem(fade(180))),
                      "BTC only": per(mem(fade()[["BTC"]])), "ETH only": per(mem(fade()[["ETH"]]))}}
(ROOT / "results/gen422.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
