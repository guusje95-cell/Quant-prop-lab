"""Gen223 (config/gen223_protocol.json): G1 / U5 without equity indices. Writes results/gen223.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0]
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(src, g)
F, S, TUNE, JUDGE, R24, VOL, PX, ME, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "R24", "VOL", "PX", "ME", "daily_book"))
u = {"__file__": str(ROOT / "scripts/gen143_families.py")}; exec(open(ROOT / "scripts/gen143_families.py").read().split("R2 = pd.DataFrame")[0], u)
import fbook as B
NE = [r for r in F.NONCRYPTO if r not in ("ES", "NQ", "RTY", "YM")]


def g1(members, lbs=(126,)):
    W = pd.DataFrame(np.nan, index=R24.index, columns=members)
    for d in ME:
        i = R24.index.get_loc(d)
        if i < max(lbs) + 5:
            continue
        s = sum(np.sign(PX.iloc[i][members] / PX.iloc[i - lb][members] - 1) for lb in lbs) / len(lbs)
        live = VOL.loc[d, members].notna() & R24[members].loc[:d].notna().iloc[-max(lbs):].all()
        W.loc[d] = (s * 0.40 / VOL.loc[d, members]).where(live, 0.0) / live.sum()
    return daily_book(W.ffill().fillna(0.0).shift(1).fillna(0.0), members)


def u5(members, n):
    return u["xs"](u["PX"].shift(21) / u["PX"].shift(252) - 1, members, n)


def svt(p, fit_end="2022-12-31"):
    sd = p.rolling(60, min_periods=40).std().shift(1); return p * (p.loc[:fit_end].std() / sd).clip(upper=2).fillna(1.0)


V = {"G1": {"cur": g1(list(F.NONCRYPTO)), "ne": g1(NE)}, "U5": {"cur": u5(list(R24.columns), 6), "ne": u5(NE, 5)}}
rep, repl = {}, {}
for n, v in V.items():
    t = {k: round(S(p, TUNE), 3) for k, p in v.items()}; rep[n] = t; print(n, t, flush=True)
    if t["ne"] > t["cur"]:
        repl[n] = svt(v["ne"])
out = {"tune": rep, "replaced": list(repl)}
if repl:
    out.update(B.judge(repl, "gen223"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen223.json", "w"), indent=1)
