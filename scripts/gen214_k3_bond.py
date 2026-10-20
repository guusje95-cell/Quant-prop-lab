"""Gen214 (config/gen214_protocol.json): pension rebalancing Treasury leg. Writes results/gen214.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
RK = pd.DataFrame({"ES": D["ES"].r, "ZN": D["ZN"].r}).dropna(); RK = RK[RK.index.weekday < 5]
VZ = (RK.ZN.rolling(60, min_periods=40).std() * np.sqrt(252))
W = pd.Series(0.0, index=RK.index); k = 5
for _, gg in RK.groupby(RK.index.to_period("M")):
    if len(gg) < k + 3:
        continue
    d0 = gg.index[-(k + 1)]; mtd = (1 + gg.loc[:d0]).prod() - 1
    W.loc[gg.index[-k:]] = (1.0 if mtd.ES > mtd.ZN else -1.0) * 0.10 / VZ.loc[d0]
p = daily_book(pd.DataFrame({"ZN": W}).fillna(0.0), ["ZN"])
s = S(p, TUNE); out = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "2010-17 / 2018-22": [round(F.sharpe(p, *F.SPLITS[0]), 3), round(F.sharpe(p, *F.SPLITS[1]), 3)], "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"K3B": p}, "gen214"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen214.json", "w"), indent=1)
