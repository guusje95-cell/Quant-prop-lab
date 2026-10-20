"""Gen215 (config/gen215_protocol.json): K3 on ES+NQ vs ES. Writes results/gen215.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
RK = pd.DataFrame({"ES": D["ES"].r, "NQ": D["NQ"].r, "ZN": D["ZN"].r}).dropna(); RK = RK[RK.index.weekday < 5]
V = RK.rolling(60).std() * np.sqrt(252)


def k3(members, k=5):
    W = pd.DataFrame(0.0, index=RK.index, columns=members); sz = 1.0 / len(members)
    for _, gg in RK.groupby(RK.index.to_period("M")):
        if len(gg) < k + 3:
            continue
        d0 = gg.index[-(k + 1)]; mtd = (1 + gg.loc[:d0]).prod() - 1; sgn = -1.0 if mtd.ES > mtd.ZN else 1.0
        for r in members:
            W.loc[gg.index[-k:], r] = sgn * 0.15 / V.loc[d0, r] * sz
    return daily_book(W.fillna(0.0), members)


Vv = {"ES": k3(["ES"]), "ESNQ": k3(["ES", "NQ"])}
t = {k: round(S(p, TUNE), 3) for k, p in Vv.items()}; print(t, "current check", round(S(B.sleeves()["K3"], TUNE), 3))
ch = max(t, key=t.get); out = {"tune": t, "chosen": ch}
if ch == "ESNQ":
    out.update(B.judge({"K3": Vv["ESNQ"]}, "gen215"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen215.json", "w"), indent=1)
