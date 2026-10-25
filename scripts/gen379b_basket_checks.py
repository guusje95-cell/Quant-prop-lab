"""Gen379b (config/gen379b_protocol.json). Writes results/gen379b.json.   cd scripts && python gen379b_basket_checks.py <v86 dump>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "scripts/gen379_basket.py").read().split("# selection")[0]
g = {"__file__": str(ROOT / "scripts/gen379_basket.py")}; sys.argv = ["x", DUMP]; exec(compile(src, "g379", "exec"), g)
P, K1, base, CS, dd, shp, per, unit, END, REF, idx = (g[k] for k in ("P", "K1", "base", "CS", "dd", "shp", "per", "unit", "END", "REF", "idx"))
B = g["B"]
kept = ["mint shock", "Coinbase hourly premium", "stablecoin impulse", "fee pressure", "Bybit crowding"]
def basket(Pd):
    Dk = pd.DataFrame({k: dd(Pd[k]) for k in kept}).loc["2022":END]; sdv = Dk.loc[:"2024"].std()
    bh = sum(Pd[k] / sdv[k] for k in kept); return bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
bh = basket(P); out = {"reference K1": [REF[0], REF[1]]}
# part 1: weight chosen on 2022-24
Hk = base.assign(**{"diversifier basket": bh}); res = {}
for m in (0.25, 0.5, 0.75, 1.0):
    ph0, W, mult = CS.portfolio_v5(Hk)
    W2 = W.copy(); W2["diversifier basket"] *= m
    Wh = W2.reindex(Hk.index.floor("D")).set_axis(Hk.index); raw = (Hk * Wh).sum(axis=1)
    rawd = raw.groupby(raw.index.floor("D")).sum(); lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    tgt = (0.15 / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    b = unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
    res[str(m)] = {"2022-24": shp(b, "2022", "2024"), "2022-26 [periods]": [shp(b), per(b)]}
best = max(res, key=lambda k: res[k]["2022-24"]); bb = res[best]["2022-26 [periods]"]
out["part 1"] = {"grid": res, "chosen m": best, "pass": bool(bb[0] >= REF[0] + 0.05 and all(bb[1][i] >= REF[1][i] for i in range(3)))}
print(json.dumps(out["part 1"]), flush=True)
# part 2: robustness of the basket alone
d = dd(bh).loc["2022":END]; yrs = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)}
pos_d = {}
def rerun(cost_mult=1.0, lag=0):
    Q = {}
    for k in kept:
        h = P[k]
        Q[k] = h
    return Q
# costs x2 / one hour later: rebuild members from their position logic via the generic approximation of re-pricing:
# turnover cost is linear in cost, so cost x2 = gross - 2 x (gross - net); lag = shift every hourly P&L component by recomputing with lagged positions.
gross = {}
src2 = src.replace("* 5 / 1e4", "* 0 / 1e4").replace("CS._from_daily_weights(w.fillna(0.0), c, 5)", "CS._from_daily_weights(w.fillna(0.0), c, 0)")
g2 = {"__file__": str(ROOT / "scripts/gen379_basket.py")}; sys.argv = ["x", DUMP]; exec(compile(src2, "g379g", "exec"), g2)
P2 = {k: P[k] - 1.0 * (g2["P"][k] - P[k]) for k in kept}                    # net - (gross - net) = cost x2
src3 = src.replace("mkd = lambda w, c: CS._from_daily_weights(w.fillna(0.0), c, 5)", "mkd = lambda w, c: CS._from_daily_weights(w.fillna(0.0).shift(1), c, 5)") \
          .replace("o[t + 1:min(t + 5, len(s))] = s[t]", "o[t + 2:min(t + 6, len(s))] = s[t]")
g3 = {"__file__": str(ROOT / "scripts/gen379_basket.py")}; sys.argv = ["x", DUMP]; exec(compile(src3, "g379l", "exec"), g3)
loo = {k: shp(basket({**P, **{k: P[k] * 0.0}})) if False else None for k in kept}
for k in kept:
    rest = [x for x in kept if x != k]; Dk = pd.DataFrame({x: dd(P[x]) for x in rest}).loc["2022":END]; sdv = Dk.loc[:"2024"].std()
    loo[k] = shp(sum(P[x] / sdv[x] for x in rest))
out["part 2"] = {"basket by calendar year": yrs, "positive years": int(sum(v > 0 for v in yrs.values())),
                 "costs x2 (2022-26)": shp(basket(P2)), "one day / one hour later (2022-26)": shp(basket(g3["P"])), "leave one member out (2022-26)": loo}
p2 = out["part 2"]
out["v9.1 candidate"] = bool(out["part 1"]["pass"] and p2["positive years"] >= 4 and p2["costs x2 (2022-26)"] >= 0.8 and p2["one day / one hour later (2022-26)"] >= 0.8)
print(json.dumps(out["part 2"]), out["v9.1 candidate"], flush=True)
(ROOT / "results/gen379b.json").write_text(json.dumps(out, indent=1)); print("DONE")
